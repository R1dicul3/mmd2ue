"""PMX 2.0 / 2.1 parser (pure parse, no semantic conversion).

Reference: docs/stage1-requirements.md §2.2 (parse correctness) and the PMX
specification (PMXEditor project). Constraints C2/C3: standard library only,
never imports unreal.

This module reads the PMX binary layout strictly per spec:
  - 'PMX ' signature + float version (2.0 / 2.1)
  - global parameter block (encoding flag, additional UV count, index byte widths)
  - fixed-order data blocks: vertices -> faces -> textures -> materials ->
    bones -> morphs -> display frames -> rigid bodies -> joints
  - string length prefix counted in BYTES
  - unknown version raises an error (do not guess)

Only the counts required by the acceptance criteria (bones, materials, morphs)
and the header/global parameters are fully materialized; per-element payloads
are parsed and counted so the whole file is walked and validated.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import BinaryIO

from mmd2ue.core.ir import ModelIR, Vertex, IR_VERSION

PMX_SIGNATURE = b"PMX "

# Encoding flag values (global setting byte 0).
ENCODING_UTF16LE = 0
ENCODING_UTF8 = 1


class ParserError(ValueError):
    """Raised on any malformed or unsupported PMX input."""


@dataclass
class _Header:
    version: float = 2.0
    encoding: str = "utf-16le"
    additional_uv: int = 0
    vertex_index_size: int = 1
    texture_index_size: int = 1
    material_index_size: int = 1
    bone_index_size: int = 1
    morph_index_size: int = 1
    rigidbody_index_size: int = 1


class _Reader:
    """Little-endian binary reader with bounds checking on every read."""

    __slots__ = ("_data", "_pos", "encoding")

    def __init__(self, data: bytes, encoding: str) -> None:
        self._data = data
        self._pos = 0
        self.encoding = encoding

    def _need(self, n: int) -> bytes:
        if n < 0:
            raise ParserError("negative read size")
        if self._pos + n > len(self._data):
            raise ParserError(
                "unexpected end of data: need %d bytes at offset %d "
                "(have %d total)" % (n, self._pos, len(self._data))
            )
        return self._data[self._pos:self._pos + n]

    def u8(self) -> int:
        b = self._need(1)
        self._pos += 1
        return b[0]

    def u16(self) -> int:
        b = self._need(2)
        self._pos += 2
        return struct.unpack("<H", b)[0]

    def u32(self) -> int:
        b = self._need(4)
        self._pos += 4
        return struct.unpack("<I", b)[0]

    def i32(self) -> int:
        b = self._need(4)
        self._pos += 4
        return struct.unpack("<i", b)[0]

    def f32(self) -> float:
        b = self._need(4)
        self._pos += 4
        return struct.unpack("<f", b)[0]

    def uindex(self, size: int) -> int:
        if size == 1:
            return self.u8()
        if size == 2:
            return self.u16()
        if size == 4:
            return self.u32()
        raise ParserError("invalid index size %d" % size)

    def skip(self, n: int) -> None:
        self._need(n)
        self._pos += n

    def vec2(self) -> tuple:
        return (self.f32(), self.f32())

    def vec3(self) -> tuple:
        return (self.f32(), self.f32(), self.f32())

    def vec4(self) -> tuple:
        return (self.f32(), self.f32(), self.f32(), self.f32())

    def text(self) -> str:
        # String length prefix is counted in BYTES (per spec), then decode.
        n = self.u32()
        raw = self._need(n)
        self._pos += n
        try:
            return raw.decode(self.encoding, errors="strict")
        except UnicodeDecodeError as e:
            raise ParserError("failed to decode string: %s" % e)


def _parse_vertex(r: _Reader, h: _Header, acc: dict) -> Vertex:
    """Parse one PMX vertex into a materialized Vertex (position/normal/uv/skin).

    ``acc`` is a mutable dict that accumulates report counters: ``approximated``
    for SDEF vertices (treated as BDEF2) and ``skipped`` for unsupported weight
    types (QDEF, type 4) that are structurally skipped so a real 2.1 asset can
    be parsed degradingly instead of the whole file failing.

    Skinning weights are normalized so the exporter can emit them directly as
    JOINTS_0/WEIGHTS_0: BDEF1 gets a single joint at weight 1.0; BDEF2/4 and
    SDEF (as BDEF2) retain up to 4 (joint, weight) pairs.
    """
    position = r.vec3()
    normal = r.vec3()
    uv = r.vec2()
    for _ in range(h.additional_uv):
        r.vec4()
    weight_type = r.u8()
    joints = []
    weights = []
    if weight_type == 0:          # BDEF1
        joints = [r.uindex(h.bone_index_size)]
        weights = [1.0]
    elif weight_type == 1:        # BDEF2
        joints = [r.uindex(h.bone_index_size), r.uindex(h.bone_index_size)]
        w = r.f32()
        weights = [w, 1.0 - w]
    elif weight_type == 2:        # BDEF4
        joints = [r.uindex(h.bone_index_size) for _ in range(4)]
        weights = [r.f32() for _ in range(4)]
        total = sum(weights)
        if total > 0.0:
            weights = [weight / total for weight in weights]
    elif weight_type == 3:        # SDEF: approximated as BDEF2 (drop C/R0/R1)
        joints = [r.uindex(h.bone_index_size), r.uindex(h.bone_index_size)]
        w = r.f32()
        weights = [w, 1.0 - w]
        r.vec3()                  # C
        r.vec3()                  # R0
        r.vec3()                  # R1
        acc["approximated"] += 1
    elif weight_type == 4:        # QDEF (PMX 2.1): skipped, skin data dropped
        for _ in range(4):
            r.uindex(h.bone_index_size)
        for _ in range(4):
            r.f32()
        acc["skipped"] += 1
    else:
        raise ParserError("unknown vertex weight type %d" % weight_type)
    edge_scale = r.f32()
    return Vertex(
        position=position, normal=normal, uv=uv,
        joints=joints, weights=weights,
        weight_type=weight_type, edge_scale=edge_scale,
    )


def _parse_material(r: _Reader) -> tuple:
    name = r.text()
    name_en = r.text()
    diffuse = r.vec4()
    specular = r.vec3()
    specular_strength = r.f32()
    ambient = r.vec3()
    flag = r.u8()
    edge_color = r.vec4()
    edge_size = r.f32()
    texture_index = r.i32()
    sphere_texture_index = r.i32()
    sphere_mode = r.u8()
    toon_flag = r.u8()
    if toon_flag == 0:
        r.u8()                    # shared toon texture index
    else:
        r.text()                  # toon texture file name
    r.text()                      # memo
    face_count = r.i32()
    return {
        "name": name, "name_en": name_en, "diffuse": diffuse, "specular": specular,
        "specular_strength": specular_strength, "ambient": ambient, "flag": flag,
        "edge_color": edge_color, "edge_size": edge_size,
        "texture_index": texture_index, "sphere_texture_index": sphere_texture_index,
        "sphere_mode": sphere_mode, "toon_flag": toon_flag, "memo": "",
        "face_count": face_count,
    }


_IK_CONSTRAINT = ("rotation", "position_x", "position_y", "position_z")


def _parse_bone(r: _Reader, h: _Header) -> dict:
    name = r.text()
    name_en = r.text()
    # PMX 2.0 bone.position is the LOCAL translation relative to its parent
    # (felixjones spec); passed through verbatim. The exporter accumulates it
    # along the parent chain to recover the model-space absolute rest transform.
    position = r.vec3()
    parent_index = r.uindex(h.bone_index_size)
    layer = r.i32()
    flag = r.u16()
    # bit flags
    target = True if flag & 0x0001 else False
    rotatable = True if flag & 0x0002 else False
    movable = True if flag & 0x0004 else False
    visible = bool(flag & 0x0008)
    operable = bool(flag & 0x0010)
    ik = bool(flag & 0x0020)
    inherit_local = bool(flag & 0x0080)
    inherit_rotation = bool(flag & 0x0100)
    inherit_translation = bool(flag & 0x0200)
    fixed_axis = bool(flag & 0x0400)
    local_axis = bool(flag & 0x0800)
    deform_after_physics = bool(flag & 0x1000)
    external_parent = bool(flag & 0x2000)

    if target:
        r.uindex(h.bone_index_size)  # target bone
    if ik:
        bone_ik = {
            "target": r.uindex(h.bone_index_size),
            "loop": r.i32(),
            "limit_rad": r.f32(),
            "links": [],
        }
        link_count = r.i32()
        for _ in range(link_count):
            ik_target = r.uindex(h.bone_index_size)
            has_limit = r.u8()
            limit_min = None
            limit_max = None
            if has_limit:
                limit_min = r.vec3()
                limit_max = r.vec3()
            bone_ik["links"].append({
                "target": ik_target,
                "has_limit": bool(has_limit),
                "limit_min": limit_min,
                "limit_max": limit_max,
            })
    else:
        bone_ik = None

    if inherit_local:
        r.uindex(h.bone_index_size)  # inherit parent
        r.f32()                       # inherit weight
    if fixed_axis:
        r.vec3()
    if local_axis:
        r.vec3()
    if external_parent:
        r.i32()                       # external parent key
    if deform_after_physics:
        r.i32()                       # deform after physics key

    return {
        "name": name, "name_en": name_en, "position": position,
        "parent_index": parent_index, "layer": layer, "flag": flag,
        "ik": bone_ik,
    }


def parse(data: bytes) -> ModelIR:
    """Parse a PMX byte buffer into ModelIR."""
    r = _Reader(data, "utf-16le")
    sig = data[:4]
    if sig != PMX_SIGNATURE:
        raise ParserError("not a PMX file: bad signature")
    r.skip(4)
    version = struct.unpack("<f", data[4:8])[0]
    r.skip(4)
    # 2.1 is stored as single-precision float and reads back as ~2.0999999.
    if not (1.99 <= version <= 2.11):
        raise ParserError(
            "unsupported PMX version %r (only 2.0 and 2.1 are supported)" % version
        )

    # Global parameter block.
    header_count = r.u8()          # always 8
    encoding_flag = r.u8()
    additional_uv = r.u8()
    vertex_index_size = r.u8()
    texture_index_size = r.u8()
    material_index_size = r.u8()
    bone_index_size = r.u8()
    morph_index_size = r.u8()
    rigidbody_index_size = r.u8()

    encoding = "utf-16le" if encoding_flag == ENCODING_UTF16LE else "utf-8"
    if header_count != 8:
        raise ParserError("unexpected global parameter count %d" % header_count)

    h = _Header(
        version=version, encoding=encoding, additional_uv=additional_uv,
        vertex_index_size=vertex_index_size, texture_index_size=texture_index_size,
        material_index_size=material_index_size, bone_index_size=bone_index_size,
        morph_index_size=morph_index_size, rigidbody_index_size=rigidbody_index_size,
    )
    r.encoding = encoding

    ir = ModelIR()
    ir.pmx_version = version
    ir.encoding = encoding
    ir.index_sizes = {
        "vertex": vertex_index_size, "texture": texture_index_size,
        "material": material_index_size, "bone": bone_index_size,
        "morph": morph_index_size, "rigid_body": rigidbody_index_size,
    }
    ir.additional_uv = additional_uv

    ir.model_name = r.text()
    ir.model_name_en = r.text()
    ir.comment = r.text()
    ir.comment_en = r.text()

    # Vertices (materialized for the glTF exporter).
    vertex_count = r.i32()
    acc = {"approximated": 0, "skipped": 0}
    vertices = [_parse_vertex(r, h, acc) for _ in range(vertex_count)]
    ir.counts["vertices"] = vertex_count
    ir.vertices = vertices

    # Faces (indices): u16 triangle vertex indices (PMX spec).
    face_index_count = r.i32()
    faces = [r.u16() for _ in range(face_index_count)]
    ir.counts["surfaces"] = face_index_count // 3
    ir.faces = faces

    # Textures (relative paths, materialized for material mapping).
    texture_count = r.i32()
    textures = [r.text() for _ in range(texture_count)]
    ir.counts["textures"] = texture_count
    ir.textures = textures

    # Materials.
    material_count = r.i32()
    mats = [_parse_material(r) for _ in range(material_count)]
    ir.counts["materials"] = material_count
    ir.materials = mats

    # Bones.
    bone_count = r.i32()
    bones = [_parse_bone(r, h) for _ in range(bone_count)]
    ir.counts["bones"] = bone_count
    ir.bones = bones

    # Morphs.
    morph_count = r.i32()
    morphs = []
    for _ in range(morph_count):
        mname = r.text()
        mname_en = r.text()
        panel = r.u8()
        mtype = r.u8()
        offsets = []
        n = r.i32()
        for _ in range(n):
            offsets.append(_parse_morph_offset(r, h, mtype))
        morphs.append({
            "name": mname, "name_en": mname_en, "panel": panel,
            "type": mtype, "offsets": offsets,
        })
    ir.counts["morphs"] = morph_count
    ir.morphs = morphs

    # Display frames.
    display_count = r.i32()
    for _ in range(display_count):
        dname = r.text()
        dname_en = r.text()
        special = r.u8()
        fn = r.i32()
        for _ in range(fn):
            ftype = r.u8()
            if ftype == 0:
                r.uindex(bone_index_size)
            else:
                r.uindex(morph_index_size)
    ir.counts["display_frames"] = display_count

    # Rigid bodies (keep count, retain as placeholders — D-M1-3 keeps fields empty).
    rb_count = r.i32()
    for _ in range(rb_count):
        r.text()                  # name
        r.text()                  # name_en
        r.uindex(bone_index_size)  # bone
        r.u8()                    # group
        r.u16()                   # no-collision group mask
        r.u8()                    # shape
        r.vec3()                  # size
        r.vec3()                  # position (local)
        r.vec3()                  # rotation (local)
        r.f32()                   # mass
        r.f32()                   # linear damping
        r.f32()                   # angular damping
        r.f32()                   # restitution
        r.f32()                   # friction
        r.u8()                    # physics mode
    ir.counts["rigid_bodies"] = rb_count

    # Joints.
    joint_count = r.i32()
    for _ in range(joint_count):
        r.text()                  # name
        r.text()                  # name_en
        r.u8()                    # type
        r.uindex(rigidbody_index_size)  # rigid A
        r.uindex(rigidbody_index_size)  # rigid B
        r.vec3()                  # position
        r.vec3()                  # rotation
        r.vec3()                  # translation lower limit
        r.vec3()                  # translation upper limit
        r.vec3()                  # rotation lower limit
        r.vec3()                  # rotation upper limit
        r.vec3()                  # spring translation
        r.vec3()                  # spring rotation
    ir.counts["joints"] = joint_count

    # units semantics (see core/ir.py module docstring): a PMX file is exactly
    # one model, so the parse report counts units = 1 (models parsed). Vertex /
    # material / bone counts are reported under ir.counts, not under units.
    ir.report = {
        "units": 1,
        "skipped": acc["skipped"],
        "approximated": acc["approximated"],
    }
    return ir


def _parse_morph_offset(r: _Reader, h: _Header, mtype: int) -> dict:
    if mtype == 0:                 # group
        return {"morph_index": r.uindex(h.morph_index_size),
                "rate": r.f32()}
    if mtype == 1:                 # vertex
        return {"vertex_index": r.uindex(h.vertex_index_size),
                "offset": r.vec3()}
    if mtype in (3, 4, 5, 6, 7):   # bone / uv / additional uv 1-4
        return {"index": r.uindex(h.vertex_index_size),
                "offset": r.vec4()}
    if mtype == 8:                 # material
        return {"material_index": r.uindex(h.material_index_size),
                "op_type": r.u8(),
                "diffuse": r.vec4(),
                "specular": r.vec3(),
                "specular_strength": r.f32(),
                "ambient": r.vec3(),
                "edge_color": r.vec4(),
                "edge_size": r.f32(),
                "texture_index": r.i32(),
                "sphere_texture_index": r.i32(),
                "sphere_mode": r.u8(),
                "toon_flag": r.u8()}
    if mtype == 9:                 # flip (group)
        return {"morph_index": r.uindex(h.morph_index_size),
                "rate": r.f32()}
    if mtype == 10:                # impulse
        return {"rigid_body_index": r.uindex(h.rigidbody_index_size),
                "is_local": r.u8(),
                "impulse": r.vec3(),
                "torque": r.vec3()}
    raise ParserError("unknown morph type %d" % mtype)


def parse_file(path: str) -> ModelIR:
    """Parse a PMX file from a filesystem path."""
    with open(path, "rb") as fh:
        return parse(fh.read())
