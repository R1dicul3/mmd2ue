"""glTF 2.0 exporter: model IR -> glTF 2.0 (.gltf JSON + .bin).

Produces a standards-compliant glTF 2.0 asset from a ModelIR:
  - asset / scene / scenes: single default scene, one or more root nodes
  - nodes: one node per bone (name preserved, parent/child hierarchy intact),
    plus a mesh node carrying the skinned mesh (skin reference)
  - skins: joints + per-bone inverseBindMatrices (inverse of each bone
    global bind transform, so bind-pose vertices restore exactly)
  - meshes: one primitive with POSITION(+min/max)/NORMAL(+min/max)/
    TEXCOORD_0(+min/max)/JOINTS_0/WEIGHTS_0 and triangle indices, packed
    into a single external .bin buffer referenced by buffers[0].uri
  - materials: MMD-approximation PBR (diffuse -> BaseColor factor; texture
    -> BaseColor texture; sphere map / toon / edge ignored and recorded)

Skinning weights are emitted verbatim from IR vertex joints/weights (BDEF1/2/4
and SDEF-as-BDEF2), satisfying M2 acceptance for JOINTS_0/WEIGHTS_0.

Materials follow ADR-007 / docs/stage2-requirements.md section 3:
  diffuse RGB(a) -> pbrMetallicRoughness.baseColorFactor
  texture_index >= 0 -> baseColorTexture (referenced image/texture/sampler)
  sphere map / toon / edge -> ignored, listed in the export report.
  External texture references (material -> texture uri) are listed in the
  report for downstream resolution (F7).

Pure standard library; never imports unreal (constraint C1). Deterministic
(C4): stable ordering, exact float serialization, no timestamps.
"""

from __future__ import annotations

import json
import os
import struct
from dataclasses import dataclass, field
from typing import Optional

from mmd2ue.core.ir import ModelIR

GLTF_VERSION = "2.0"

# glTF component types.
UNSIGNED_BYTE = 5121
UNSIGNED_SHORT = 5123
UNSIGNED_INT = 5125
FLOAT = 5126

# bufferView targets.
ARRAY_BUFFER = 34962
ELEMENT_ARRAY_BUFFER = 34963


class ExportError(ValueError):
    """Raised when the IR cannot be exported to glTF (structural problem)."""


@dataclass
class ExportReport:
    """Summary of one export run, incl. approximated/ignored material items.

    Carries the canonical units/skipped/approximated keys (parser
    convention: units = processed unit count, skipped = skipped items,
    approximated = SDEF-as-BDEF2 count) plus the per-material ignored list
    (sphere map / toon / edge) and the external texture reference list.
    """

    bone_count: int = 0
    vertex_count: int = 0
    triangle_count: int = 0
    joint_count: int = 0
    material_count: int = 0
    texture_count: int = 0
    sdef_approximated: int = 0
    skipped_weights: int = 0
    ignored_materials: dict = field(default_factory=dict)
    texture_refs: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            # Canonical keys (parser convention, required by M2 gate).
            "units": self.vertex_count,
            "skipped": self.skipped_weights,
            "approximated": self.sdef_approximated,
            # Detailed counts.
            "bone_count": self.bone_count,
            "vertex_count": self.vertex_count,
            "triangle_count": self.triangle_count,
            "joint_count": self.joint_count,
            "material_count": self.material_count,
            "texture_count": self.texture_count,
            "sdef_approximated": self.sdef_approximated,
            "skipped_weights": self.skipped_weights,
            "ignored_materials": [
                {"material_index": idx, "name": name, "items": items}
                for idx, (name, items) in sorted(self.ignored_materials.items())
            ],
            "texture_refs": [
                {"material_index": idx, "name": name, "texture_uri": uri}
                for idx, (name, uri) in sorted(self.texture_refs.items())
            ],
        }


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _identity_matrix() -> list:
    """Column-major 4x4 identity (glTF matrix convention)."""
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def _translation_matrix(x, y, z) -> list:
    """Column-major 4x4 translation (glTF convention)."""
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        float(x), float(y), float(z), 1.0,
    ]


def _mat4_mul(a: list, b: list) -> list:
    """Column-major 4x4 matrix multiply (a * b)."""
    out = [0.0] * 16
    for col in range(4):
        for row in range(4):
            s = 0.0
            for k in range(4):
                s += a[k * 4 + row] * b[col * 4 + k]
            out[col * 4 + row] = s
    return out


def _translation_inverse(x, y, z) -> list:
    """Inverse of a translation matrix == translate by (-x,-y,-z)."""
    return _translation_matrix(-x, -y, -z)


def _bone_world_translations(bones) -> list:
    """Return each bone's absolute (model-space) rest translation (x, y, z).

    PMX stores bone.position as the LOCAL translation relative to its parent
    (felixjones PMX 2.0 spec: "Position | vec3 | The local translation of the
    bone"). The absolute rest transform of a bone is therefore
    translate(parent_absolute + position); accumulate along the parent chain
    (PMX convention: a bone's parent is defined before the bone itself).
    Returns one tuple per bone (accumulated model-space translation).
    """
    n = len(bones)
    world = [None] * n

    def resolve(idx: int) -> tuple:
        if world[idx] is not None:
            return world[idx]
        bone = bones[idx]
        position = bone.get("position", (0.0, 0.0, 0.0))
        ax = float(position[0]) if len(position) > 0 else 0.0
        ay = float(position[1]) if len(position) > 1 else 0.0
        az = float(position[2]) if len(position) > 2 else 0.0
        parent = bone.get("parent_index", -1)
        if isinstance(parent, int) and 0 <= parent < n and parent != idx:
            px, py, pz = resolve(parent)
        else:
            px = py = pz = 0.0
        world[idx] = (px + ax, py + ay, pz + az)
        return world[idx]

    for idx in range(n):
        resolve(idx)
    return world



class _BufferBuilder:
    """Accumulate binary payloads and remember (offset, length) per view."""

    __slots__ = ("_chunks", "_offset")

    def __init__(self) -> None:
        self._chunks = []
        self._offset = 0

    def add(self, data: bytes, align: int = 1):
        """Append ``data`` (aligned) and return (offset, byteLength)."""
        pad = (-self._offset) % align
        if pad:
            self._chunks.append(b"\x00" * pad)
            self._offset += pad
        offset = self._offset
        self._chunks.append(data)
        self._offset += len(data)
        return offset, len(data)

    def build(self) -> bytes:
        return b"".join(self._chunks)


def _pack_floats(values):
    return struct.pack("<%df" % len(values), *values)


def _pack_u8(values):
    return struct.pack("<%dB" % len(values), *values)


def _pack_u16(values):
    return struct.pack("<%dH" % len(values), *values)


def _pack_u32(values):
    return struct.pack("<%dI" % len(values), *values)


def _compute_min_max(flat_values, arity):
    """Compute per-component min/max over a flat list of arity-tuples.

    Returns (min_list, max_list) each of length ``arity``, or (None, None)
    when ``flat_values`` is empty. Used for POSITION/NORMAL/TEXCOORD min/max.
    """
    count = len(flat_values) // arity
    if count == 0:
        return None, None
    mins = list(flat_values[:arity])
    maxs = list(flat_values[:arity])
    for i in range(1, count):
        for c in range(arity):
            v = flat_values[i * arity + c]
            if v < mins[c]:
                mins[c] = v
            if v > maxs[c]:
                maxs[c] = v
    return mins, maxs


def _add_accessor(buffer_builder, buffer_views, accessors, data,
                  component_type, type_, target=ARRAY_BUFFER,
                  min_val=None, max_val=None):
    """Append ``data``, add a bufferView + accessor, return accessor index.

    ``min_val``/``max_val`` (optional) are per-component bounds written
    onto the accessor (glTF requires min/max on POSITION).
    """
    comp_size = {FLOAT: 4, UNSIGNED_BYTE: 1, UNSIGNED_SHORT: 2,
                 UNSIGNED_INT: 4}[component_type]
    offset, length = buffer_builder.add(data, align=comp_size)
    view_index = len(buffer_views)
    buffer_views.append({
        "buffer": 0,
        "byteOffset": offset,
        "byteLength": length,
        "target": target,
    })
    elem_count = {"VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16, "SCALAR": 1}[type_]
    count = length // (comp_size * elem_count)
    accessor = {
        "bufferView": view_index,
        "componentType": component_type,
        "count": count,
        "type": type_,
    }
    if min_val is not None:
        accessor["min"] = [float(v) for v in min_val]
    if max_val is not None:
        accessor["max"] = [float(v) for v in max_val]
    accessors.append(accessor)
    return len(accessors) - 1


def _build_children(bones):
    """Map parent_index -> list of child bone indices (excludes self-loops)."""
    children = {i: [] for i in range(len(bones))}
    for idx, bone in enumerate(bones):
        parent = bone.get("parent_index", -1)
        if isinstance(parent, int) and 0 <= parent < len(bones) and parent != idx:
            children[parent].append(idx)
    return children


def _roots(bones):
    """Bone indices whose parent_index is -1, self, or out of range."""
    roots = []
    for idx, bone in enumerate(bones):
        parent = bone.get("parent_index", -1)
        if not (isinstance(parent, int) and 0 <= parent < len(bones) and parent != idx):
            roots.append(idx)
    return roots



def export_gltf(ir: ModelIR, buffer_uri: str = "model.bin"):
    """Convert a ModelIR into (glTF dict, .bin bytes, ExportReport).

    ``buffer_uri`` is the relative URI stored on buffers[0] (F1): a .gltf
    with an external .bin must reference it via uri. The returned dict
    serializes to a .gltf file; the returned bytes are the .bin buffer.
    """
    report = ExportReport()

    bones = list(ir.bones)
    vertices = list(ir.vertices)
    faces = list(ir.faces)
    materials = list(ir.materials)
    textures = list(ir.textures)
    report.bone_count = len(bones)
    report.vertex_count = len(vertices)
    report.material_count = len(materials)
    report.texture_count = len(textures)
    report.sdef_approximated = ir.report.get("approximated", 0)
    report.skipped_weights = ir.report.get("skipped", 0)
    report.triangle_count = len(faces) // 3
    report.joint_count = len(bones)

    if len(faces) % 3 != 0:
        raise ExportError("face index count %d is not a multiple of 3" % len(faces))

    # ---- Nodes: one per bone (names + hierarchy) ----
    # F8: PMX bone.position is the LOCAL translation relative to its parent
    # (felixjones PMX 2.0 spec), which is exactly what a glTF node translation
    # means, so we write it verbatim (no absolute/relative conversion).
    nodes = []
    for idx, bone in enumerate(bones):
        name = bone.get("name") or bone.get("name_en") or ("bone_%d" % idx)
        position = bone.get("position", (0.0, 0.0, 0.0))
        tx = float(position[0]) if len(position) > 0 else 0.0
        ty = float(position[1]) if len(position) > 1 else 0.0
        tz = float(position[2]) if len(position) > 2 else 0.0
        node = {"name": name}
        if tx or ty or tz:
            node["translation"] = [tx, ty, tz]
        nodes.append(node)

    # ---- Materials (MMD approximation) ----
    materials_out = []
    images = []
    textures_out = []
    samplers = [{"magFilter": 9729, "minFilter": 9729,
                 "wrapS": 10497, "wrapT": 10497}]
    tex_cache = {}  # IR texture index -> glTF texture index

    for mat_idx, mat in enumerate(materials):
        name = mat.get("name") or mat.get("name_en") or ("mat_%d" % mat_idx)
        diffuse = mat.get("diffuse", (1.0, 1.0, 1.0, 1.0))
        base = [
            _clamp01(float(diffuse[0]) if len(diffuse) > 0 else 1.0),
            _clamp01(float(diffuse[1]) if len(diffuse) > 1 else 1.0),
            _clamp01(float(diffuse[2]) if len(diffuse) > 2 else 1.0),
            _clamp01(float(diffuse[3]) if len(diffuse) > 3 else 1.0),
        ]
        pbr = {
            "baseColorFactor": base,
            "metallicFactor": 0.0,
            "roughnessFactor": 1.0,
        }
        gltf_mat = {"name": name, "pbrMetallicRoughness": pbr}

        tex_idx = mat.get("texture_index", -1)
        if (isinstance(tex_idx, int) and 0 <= tex_idx < len(textures)
                and textures[tex_idx]):
            uri = textures[tex_idx]
            g = tex_cache.get(tex_idx)
            if g is None:
                images.append({"uri": uri})
                textures_out.append({"source": len(images) - 1, "sampler": 0})
                g = len(textures_out) - 1
                tex_cache[tex_idx] = g
            pbr["baseColorTexture"] = {"index": g}
            # Record the external texture reference (F7).
            report.texture_refs[mat_idx] = (name, uri)

        ignored = []
        if mat.get("sphere_mode", 0) not in (0, None):
            ignored.append("sphere_map")
        else:
            sphere_tex = mat.get("sphere_texture_index", -1)
            if isinstance(sphere_tex, int) and sphere_tex >= 0:
                ignored.append("sphere_map")
        if mat.get("toon_flag", 0) not in (0, None):
            ignored.append("toon")
        ignored.append("edge")  # edge outline always ignored in v1
        if ignored:
            report.ignored_materials[mat_idx] = (name, ignored)
        materials_out.append(gltf_mat)

    # ---- Mesh: one primitive ----
    buffer_builder = _BufferBuilder()
    accessors = []
    buffer_views = []
    primitive_attributes = {}

    if vertices:
        positions = []
        normals = []
        uvs = []
        joints_flat = []
        weights_flat = []
        for v in vertices:
            p = v.position if hasattr(v, "position") else v.get("position", (0.0, 0.0, 0.0))
            positions.extend((float(p[0]), float(p[1]), float(p[2])))
            n = v.normal if hasattr(v, "normal") else v.get("normal", (0.0, 0.0, 1.0))
            normals.extend((float(n[0]), float(n[1]), float(n[2])))
            uv = v.uv if hasattr(v, "uv") else v.get("uv", (0.0, 0.0))
            # glTF V axis is flipped vs MMD UV.
            uvs.extend((float(uv[0]), 1.0 - float(uv[1])))
            j = list(v.joints if hasattr(v, "joints") else v.get("joints", []))
            w = list(v.weights if hasattr(v, "weights") else v.get("weights", []))
            j = j[:4]
            w = w[:4]
            while len(j) < 4:
                j.append(0)
                w.append(0.0)
            joints_flat.extend(int(x) for x in j)
            weights_flat.extend(float(x) for x in w)

        # POSITION with min/max (F4).
        pos_min, pos_max = _compute_min_max(positions, 3)
        primitive_attributes["POSITION"] = _add_accessor(
            buffer_builder, buffer_views, accessors,
            _pack_floats(positions), FLOAT, "VEC3",
            min_val=pos_min, max_val=pos_max)
        # NORMAL with min/max.
        nrm_min, nrm_max = _compute_min_max(normals, 3)
        primitive_attributes["NORMAL"] = _add_accessor(
            buffer_builder, buffer_views, accessors,
            _pack_floats(normals), FLOAT, "VEC3",
            min_val=nrm_min, max_val=nrm_max)
        # TEXCOORD_0 with min/max.
        uv_min, uv_max = _compute_min_max(uvs, 2)
        primitive_attributes["TEXCOORD_0"] = _add_accessor(
            buffer_builder, buffer_views, accessors,
            _pack_floats(uvs), FLOAT, "VEC2",
            min_val=uv_min, max_val=uv_max)
        # F8-low: JOINTS_0 uses UNSIGNED_BYTE only up to 256 bones (indices
        # 0..255); beyond that, upgrade to UNSIGNED_SHORT to avoid overflow.
        if len(bones) > 256:
            joints_data = _pack_u16(joints_flat)
            joints_component = UNSIGNED_SHORT
        else:
            joints_data = _pack_u8(joints_flat)
            joints_component = UNSIGNED_BYTE
        primitive_attributes["JOINTS_0"] = _add_accessor(
            buffer_builder, buffer_views, accessors,
            joints_data, joints_component, "VEC4")
        primitive_attributes["WEIGHTS_0"] = _add_accessor(
            buffer_builder, buffer_views, accessors,
            _pack_floats(weights_flat), FLOAT, "VEC4")

    idx_accessor = None
    if faces:
        if len(vertices) > 65535:
            idx_data = _pack_u32([int(x) for x in faces])
            idx_comp = UNSIGNED_INT
        else:
            idx_data = _pack_u16([int(x) for x in faces])
            idx_comp = UNSIGNED_SHORT
        idx_accessor = _add_accessor(
            buffer_builder, buffer_views, accessors, idx_data, idx_comp,
            "SCALAR", target=ELEMENT_ARRAY_BUFFER)

    meshes = []
    mesh_node_index = None
    if vertices:
        primitive = {"attributes": primitive_attributes, "mode": 4}
        if idx_accessor is not None:
            primitive["indices"] = idx_accessor
        if materials_out:
            primitive["material"] = 0
        meshes.append({"primitives": [primitive]})
        mesh_node_index = len(nodes)
        mesh_node = {"name": "Mesh", "mesh": 0}
        if bones:
            mesh_node["skin"] = 0
        nodes.append(mesh_node)

    # ---- Skins: inverseBindMatrices = inverse(absolute bind transform) (F2/F8) ----
    # The bind transform of a bone is its ABSOLUTE (model-space) translation,
    # accumulated along the parent chain from the local bone.position values;
    # its inverse is translate(-world). Composing the node translations recovers
    # each bone absolute transform, so global*IBM == identity at bind pose.
    unbind_meta = None
    if bones:
        world_positions = _bone_world_translations(bones)
        inv_bind_values = []
        for (ax, ay, az) in world_positions:
            inv_bind_values.extend(_translation_inverse(ax, ay, az))
        unbind_meta = _add_accessor(
            buffer_builder, buffer_views, accessors,
            _pack_floats(inv_bind_values), FLOAT, "MAT4")

    bin_data = buffer_builder.build()

    # ---- Assemble asset ----
    gltf = {
        "asset": {"version": GLTF_VERSION, "generator": "mmd2ue-core-gltf"},
        "scene": 0,
    }

    # Attach children to bone nodes.
    if bones:
        children = _build_children(bones)
        for idx in range(len(bones)):
            if children.get(idx):
                nodes[idx]["children"] = list(children[idx])
        roots = _roots(bones)
        if mesh_node_index is not None and roots:
            nodes[roots[0]]["children"] = (
                nodes[roots[0]].get("children", []) + [mesh_node_index])
        scene_nodes = roots if roots else [0]
    else:
        scene_nodes = [mesh_node_index] if mesh_node_index is not None else []

    if nodes:
        gltf["nodes"] = nodes
    if meshes:
        gltf["meshes"] = meshes
    if materials_out:
        gltf["materials"] = materials_out
    if images:
        gltf["images"] = images
    if textures_out:
        gltf["textures"] = textures_out
    gltf["samplers"] = samplers
    if accessors:
        gltf["accessors"] = accessors
    if buffer_views:
        gltf["bufferViews"] = buffer_views
    # F1: buffers[0] must carry a uri (external .bin).
    gltf["buffers"] = [{"byteLength": len(bin_data), "uri": buffer_uri}]
    gltf["scenes"] = [{"nodes": scene_nodes}]
    if bones:
        gltf["skins"] = [{
            "joints": list(range(len(bones))),
            "inverseBindMatrices": unbind_meta,
        }]

    return gltf, bin_data, report



def export_gltf_json(ir: ModelIR, indent: int = 2, buffer_uri: str = "model.bin") -> str:
    """Serialize the glTF JSON (without .bin) as a string (deterministic)."""
    gltf, _bin_data, _report = export_gltf(ir, buffer_uri=buffer_uri)
    return json.dumps(gltf, ensure_ascii=False, indent=indent) + "\n"


def export_gltf_files(ir: ModelIR, gltf_path: str, bin_path: str) -> ExportReport:
    """Write .gltf + .bin files to disk; return the export report.

    The .gltf buffers[0].uri is set to the basename of ``bin_path`` so the
    external .bin is correctly referenced (F1).
    """
    bin_uri = os.path.basename(bin_path)
    gltf, bin_data, report = export_gltf(ir, buffer_uri=bin_uri)
    with open(bin_path, "wb") as fh:
        fh.write(bin_data)
    text = json.dumps(gltf, ensure_ascii=False, indent=2) + "\n"
    with open(gltf_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return report

