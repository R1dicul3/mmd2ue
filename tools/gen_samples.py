"""Generate minimal synthetic PMX/VMD samples + golden IR JSON (no real assets).

This script builds the smallest valid PMX 2.0 / 2.1 files (UTF-16LE and UTF-8)
and a VMD file entirely from scratch, then writes the corresponding "golden"
IR JSON under tests/golden/. These synthetic samples are the only files ever
placed under samples/ — no real model assets (constraint C5).

Usage: python tools/gen_samples.py
"""

from __future__ import annotations

import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAMPLES = os.path.join(ROOT, "samples")
GOLDEN = os.path.join(ROOT, "tests", "golden")
os.makedirs(SAMPLES, exist_ok=True)
os.makedirs(GOLDEN, exist_ok=True)


def _pack_str(text: str, enc: str) -> bytes:
    raw = text.encode(enc)
    return struct.pack("<I", len(raw)) + raw


def _text(text: str, enc: str) -> bytes:
    return text.encode(enc)


def build_pmx_v2(version: float, encoding: str) -> bytes:
    """Clean minimal PMX with 2 bones, 1 material, 1 morph. Correct root indices."""
    enc_flag = 0 if encoding == "utf-16le" else 1
    bone_idx = struct.Struct("<B")
    out = bytearray()
    out += b"PMX " + struct.pack("<f", version)
    out += struct.pack("<B", 8)
    out += struct.pack("<B", enc_flag)
    out += struct.pack("<B", 0)
    for _ in range(6):
        out += struct.pack("<B", 1)
    # metadata
    out += _pack_str("synthetic", encoding)
    out += _pack_str("synthetic-en", encoding)
    out += _pack_str("synthetic comment", encoding)
    out += _pack_str("synthetic comment", encoding)
    # vertices: 1
    out += struct.pack("<i", 1)
    out += struct.pack("<3f", 0, 0, 0)
    out += struct.pack("<3f", 0, 0, 1)
    out += struct.pack("<2f", 0, 0)
    out += struct.pack("<B", 0)   # BDEF1
    out += struct.pack("<B", 0)   # bone 0
    out += struct.pack("<f", 1.0)
    # faces: 1 tri
    out += struct.pack("<i", 3)
    out += struct.pack("<3H", 0, 0, 0)
    # textures: 0
    out += struct.pack("<i", 0)
    # materials: 1
    out += struct.pack("<i", 1)
    out += _pack_str("mat1", encoding)
    out += _pack_str("mat1", encoding)
    out += struct.pack("<4f", 1, 1, 1, 1)
    out += struct.pack("<3f", 0, 0, 0)
    out += struct.pack("<f", 0)
    out += struct.pack("<3f", 0, 0, 0)
    out += struct.pack("<B", 0)
    out += struct.pack("<4f", 0, 0, 0, 1)
    out += struct.pack("<f", 1.0)
    out += struct.pack("<i", -1)
    out += struct.pack("<i", -1)
    out += struct.pack("<B", 0)
    out += struct.pack("<B", 0)
    out += struct.pack("<B", 0)
    out += _pack_str("", encoding)
    out += struct.pack("<i", 3)
    # bones: 2
    out += struct.pack("<i", 2)
    for bname in ("center", "arm"):
        out += _pack_str(bname, encoding)
        out += _pack_str(bname, encoding)
        out += struct.pack("<3f", 0, 0, 0)
        out += bone_idx.pack(0)          # parent index (u8) — root uses self/0
        out += struct.pack("<i", 0)       # layer
        out += struct.pack("<H", 0x0008 | 0x0002 | 0x0004)  # visible|rotatable|movable
        out += struct.pack("<3f", 0, 1, 0)  # tail position (vec3, spec-required)
    # morphs: 1 (vertex)
    out += struct.pack("<i", 1)
    out += _pack_str("smile", encoding)
    out += _pack_str("smile", encoding)
    out += struct.pack("<B", 4)
    out += struct.pack("<B", 1)
    out += struct.pack("<i", 1)
    out += struct.pack("<B", 0)
    out += struct.pack("<3f", 0, 0.1, 0)
    # display frames: 0
    out += struct.pack("<i", 0)
    # rigid bodies: 0
    out += struct.pack("<i", 0)
    # joints: 0
    out += struct.pack("<i", 0)
    return bytes(out)


def build_pmx_gltf(version: float = 2.0, encoding: str = "utf-16le") -> bytes:
    """Synthetic PMX exercising the M2 glTF path:

    - 2 bones with a real parent/child hierarchy (root -> child)
    - 3 vertices, one triangle, all BDEF2 (root/child equal weights)
    - 1 texture + 1 material with diffuse + texture + sphere map + toon + edge

    Used by the glTF golden test (tests/golden/test_gltf_golden.py) and the
    verify_all glTF report check. Programmatically generated (no real assets).
    """
    enc_flag = 0 if encoding == "utf-16le" else 1
    out = bytearray()
    out += b"PMX " + struct.pack("<f", version)
    out += struct.pack("<B", 8)
    out += struct.pack("<B", enc_flag)
    out += struct.pack("<B", 0)
    for _ in range(6):
        out += struct.pack("<B", 1)   # index sizes (bone idx, etc.)
    # metadata
    out += _pack_str("gltf-synthetic", encoding)
    out += _pack_str("gltf-synthetic-en", encoding)
    out += _pack_str("gltf synthetic", encoding)
    out += _pack_str("gltf synthetic", encoding)
    # vertices: 3 (a single triangle), BDEF2 root/child 50/50
    out += struct.pack("<i", 3)
    verts = [
        ((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0)),
        ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0)),
        ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0)),
    ]
    for pos, nrm, uv in verts:
        out += struct.pack("<3f", *pos)
        out += struct.pack("<3f", *nrm)
        out += struct.pack("<2f", *uv)
        out += struct.pack("<B", 1)   # BDEF2
        out += struct.pack("<B", 0)   # bone 0 (root)
        out += struct.pack("<B", 1)   # bone 1 (child)
        out += struct.pack("<f", 0.5)  # weight
        out += struct.pack("<f", 1.0)  # edge scale
    # faces: 1 triangle (0, 1, 2)
    out += struct.pack("<i", 3)
    out += struct.pack("<3H", 0, 1, 2)
    # textures: 1
    out += struct.pack("<i", 1)
    out += _pack_str("diffuse.png", encoding)
    # materials: 1 (texture + sphere + toon + edge)
    out += struct.pack("<i", 1)
    out += _pack_str("skin", encoding)
    out += _pack_str("skin", encoding)
    out += struct.pack("<4f", 0.8, 0.6, 0.4, 1.0)   # diffuse
    out += struct.pack("<3f", 0.1, 0.1, 0.1)        # specular
    out += struct.pack("<f", 10.0)                   # specular strength
    out += struct.pack("<3f", 0.0, 0.0, 0.0)        # ambient
    out += struct.pack("<B", 0x09)                  # flag (edge enabled 0x08 | draw 0x01)
    out += struct.pack("<4f", 0.0, 0.0, 0.0, 1.0)   # edge color
    out += struct.pack("<f", 0.5)                    # edge size
    out += struct.pack("<i", 0)                      # texture_index = 0
    out += struct.pack("<i", 0)                      # sphere_texture_index = 0
    out += struct.pack("<B", 1)                      # sphere_mode = 1 (multiply)
    out += struct.pack("<B", 1)                      # toon_flag = 1 (toon file)
    out += _pack_str("toon00.bmp", encoding)         # toon texture file name
    out += _pack_str("", encoding)                   # memo
    out += struct.pack("<i", 3)                      # face_count = 1 tri
    # bones: 2 (root -> child hierarchy)
    out += struct.pack("<i", 2)
    # bone 0: root (parent_index = 0, self/root)
    out += _pack_str("root", encoding)
    out += _pack_str("root", encoding)
    out += struct.pack("<3f", 0.0, 0.0, 0.0)
    out += struct.pack("<B", 0)       # parent = 0 (root)
    out += struct.pack("<i", 0)        # layer
    out += struct.pack("<H", 0x0008 | 0x0002 | 0x0004)
    out += struct.pack("<3f", 0, 1, 0)  # tail position (vec3)
    # bone 1: child (parent_index = 0)
    out += _pack_str("child", encoding)
    out += _pack_str("child", encoding)
    out += struct.pack("<3f", 0.0, 1.0, 0.0)
    out += struct.pack("<B", 0)       # parent = 0
    out += struct.pack("<i", 0)        # layer
    out += struct.pack("<H", 0x0008 | 0x0002 | 0x0004)
    out += struct.pack("<3f", 0, 1, 0)  # tail position (vec3)
    # morphs: 0
    out += struct.pack("<i", 0)
    # display frames: 0
    out += struct.pack("<i", 0)
    # rigid bodies: 0
    out += struct.pack("<i", 0)
    # joints: 0
    out += struct.pack("<i", 0)
    return bytes(out)

def build_pmx_gltf_chain(version: float = 2.0, encoding: str = "utf-16le") -> bytes:
    """Synthetic PMX with a 3-bone chain whose parent bones are NOT at origin.

    Exercises the F8 coordinate semantics: PMX bone.position is the LOCAL
    (parent-relative) translation, so hips=(0,8,0) -> spine=(0,1,0) ->
    head=(0,11,0) are the stored offsets. The glTF exporter writes them verbatim
    as node translations and accumulates the absolute rest transform for
    inverseBindMatrices, so the world bone positions reconstruct
    hips=(0,8,0) -> spine=(0,9,0) -> head=(0,20,0) and the bind pose restores
    the vertex. Also carries a minimal material (name + diffuse only) so the
    exporter defensive .get() fallbacks (F10) are exercised.
    """
    enc_flag = 0 if encoding == "utf-16le" else 1
    out = bytearray()
    out += b"PMX " + struct.pack("<f", version)
    out += struct.pack("<B", 8)
    out += struct.pack("<B", enc_flag)
    out += struct.pack("<B", 0)
    for _ in range(6):
        out += struct.pack("<B", 1)   # index sizes
    # metadata
    out += _pack_str("chain-synthetic", encoding)
    out += _pack_str("chain-synthetic-en", encoding)
    out += _pack_str("chain", encoding)
    out += _pack_str("chain", encoding)
    # vertices: 1, BDEF1 to head (bone 2), position at head absolute (0,20,0)
    out += struct.pack("<i", 1)
    out += struct.pack("<3f", 0.0, 20.0, 0.0)   # position
    out += struct.pack("<3f", 0.0, 0.0, 1.0)    # normal
    out += struct.pack("<2f", 0.0, 0.0)         # uv
    out += struct.pack("<B", 0)                 # BDEF1
    out += struct.pack("<B", 2)                 # bone 2 (head)
    out += struct.pack("<f", 1.0)               # edge scale
    # faces: 1 degenerate triangle
    out += struct.pack("<i", 3)
    out += struct.pack("<3H", 0, 0, 0)
    # textures: 0
    out += struct.pack("<i", 0)
    # materials: 1 (minimal: name + diffuse only)
    out += struct.pack("<i", 1)
    out += _pack_str("skin", encoding)
    out += _pack_str("skin", encoding)
    out += struct.pack("<4f", 0.5, 0.5, 0.5, 1.0)   # diffuse
    out += struct.pack("<3f", 0.0, 0.0, 0.0)        # specular
    out += struct.pack("<f", 0.0)                    # specular strength
    out += struct.pack("<3f", 0.0, 0.0, 0.0)        # ambient
    out += struct.pack("<B", 0)                     # flag
    out += struct.pack("<4f", 0.0, 0.0, 0.0, 1.0)   # edge color
    out += struct.pack("<f", 1.0)                    # edge size
    out += struct.pack("<i", -1)                     # texture_index
    out += struct.pack("<i", -1)                     # sphere_texture_index
    out += struct.pack("<B", 0)                      # sphere_mode
    out += struct.pack("<B", 0)                      # toon_flag (shared)
    out += struct.pack("<B", 0)                      # shared toon index
    out += _pack_str("", encoding)                   # memo
    out += struct.pack("<i", 1)                      # face_count
    # bones: 3 (hips -> spine -> head), parent-relative LOCAL positions
    # (PMX spec: bone.position is the local translation relative to its
    # parent, so spine = +1 above hips, head = +11 above spine).
    out += struct.pack("<i", 3)
    bone_defs = [
        ("hips", (0.0, 8.0, 0.0), 0),
        ("spine", (0.0, 1.0, 0.0), 0),
        ("head", (0.0, 11.0, 0.0), 1),
    ]
    for bname, pos, parent in bone_defs:
        out += _pack_str(bname, encoding)
        out += _pack_str(bname, encoding)
        out += struct.pack("<3f", *pos)
        out += struct.pack("<B", parent)      # parent index (u8)
        out += struct.pack("<i", 0)           # layer
        out += struct.pack("<H", 0x0008 | 0x0002 | 0x0004)
        out += struct.pack("<3f", 0, 1, 0)  # tail position (vec3)
    # morphs: 0
    out += struct.pack("<i", 0)
    # display frames: 0
    out += struct.pack("<i", 0)
    # rigid bodies: 0
    out += struct.pack("<i", 0)
    # joints: 0
    out += struct.pack("<i", 0)
    return bytes(out)


def build_vmd() -> bytes:
    out = bytearray()
    out += b"Vocaloid Motion Data 0002" + b"\x00" * 5
    out += "synthetic".encode("cp932").ljust(20, b"\x00")  # model name (20 bytes)
    # bone frames: 2
    out += struct.pack("<I", 2)
    for fname, fno in (("center", 0), ("arm", 30)):
        out += fname.encode("cp932").ljust(15, b"\x00")
        out += struct.pack("<I", fno)
        out += struct.pack("<3f", 0, 0, 0)          # position
        out += struct.pack("<4f", 0, 0, 0, 1)      # rotation quaternion
        out += bytes(64)                            # interpolation
    # morph frames: 1
    out += struct.pack("<I", 1)
    out += "smile".encode("cp932").ljust(15, b"\x00")
    out += struct.pack("<I", 0)
    out += struct.pack("<f", 1.0)
    # camera frames: 2
    out += struct.pack("<I", 2)
    for fno in (0, 30):
        out += struct.pack("<I", fno)
        out += struct.pack("<f", 10.0)              # distance
        out += struct.pack("<3f", 0, 5, -10)        # position
        out += struct.pack("<3f", 0, 0, 0)          # rotation
        out += bytes(24)                            # interpolation
        out += struct.pack("<I", 30)                # fov
        out += struct.pack("<B", 1)                 # perspective
    # light frames: 0
    out += struct.pack("<I", 0)
    # self shadow: 0
    out += struct.pack("<I", 0)
    # ik: 0
    out += struct.pack("<I", 0)
    return bytes(out)


def build_pmx_sdef(version: float = 2.0, encoding: str = "utf-16le") -> bytes:
    """Minimal PMX whose single vertex uses SDEF (weight type 3)."""
    enc_flag = 0 if encoding == "utf-16le" else 1
    bone_idx = struct.Struct("<B")
    out = bytearray()
    out += b"PMX " + struct.pack("<f", version)
    out += struct.pack("<B", 8)
    out += struct.pack("<B", enc_flag)
    out += struct.pack("<B", 0)          # additional uv
    for _ in range(6):
        out += struct.pack("<B", 1)
    out += _pack_str("synthetic", encoding)
    out += _pack_str("synthetic-en", encoding)
    out += _pack_str("synthetic comment", encoding)
    out += _pack_str("synthetic comment", encoding)
    # vertices: 1 (SDEF)
    out += struct.pack("<i", 1)
    out += struct.pack("<3f", 0, 0, 0)   # position
    out += struct.pack("<3f", 0, 0, 1)   # normal
    out += struct.pack("<2f", 0, 0)      # uv
    out += struct.pack("<B", 3)          # SDEF
    out += struct.pack("<B", 0)          # bone 0
    out += struct.pack("<B", 1)          # bone 1
    out += struct.pack("<f", 0.5)        # weight
    out += struct.pack("<3f", 1, 0, 0)   # C
    out += struct.pack("<3f", 1, 0, 0)   # R0
    out += struct.pack("<3f", 0, 1, 0)   # R1
    out += struct.pack("<f", 1.0)        # edge scale
    # faces: 0
    out += struct.pack("<i", 0)
    # textures: 0
    out += struct.pack("<i", 0)
    # materials: 1 (minimal)
    out += struct.pack("<i", 1)
    out += _pack_str("mat1", encoding)
    out += _pack_str("mat1", encoding)
    out += struct.pack("<4f", 1, 1, 1, 1)
    out += struct.pack("<3f", 0, 0, 0)
    out += struct.pack("<f", 0)
    out += struct.pack("<3f", 0, 0, 0)
    out += struct.pack("<B", 0)
    out += struct.pack("<4f", 0, 0, 0, 1)
    out += struct.pack("<f", 1.0)
    out += struct.pack("<i", -1)
    out += struct.pack("<i", -1)
    out += struct.pack("<B", 0)
    out += struct.pack("<B", 0)
    out += struct.pack("<B", 0)
    out += _pack_str("", encoding)
    out += struct.pack("<i", 3)
    # bones: 2
    out += struct.pack("<i", 2)
    for bname in ("center", "arm"):
        out += _pack_str(bname, encoding)
        out += _pack_str(bname, encoding)
        out += struct.pack("<3f", 0, 0, 0)
        out += bone_idx.pack(0)
        out += struct.pack("<i", 0)
        out += struct.pack("<H", 0x0008 | 0x0002 | 0x0004)
        out += struct.pack("<3f", 0, 1, 0)  # tail position (vec3)
    # morphs: 0
    out += struct.pack("<i", 0)
    # display frames: 0
    out += struct.pack("<i", 0)
    # rigid bodies: 0
    out += struct.pack("<i", 0)
    # joints: 0
    out += struct.pack("<i", 0)
    return bytes(out)


def build_pmx_qdef(version: float = 2.1, encoding: str = "utf-8") -> bytes:
    """Minimal PMX 2.1 whose single vertex uses QDEF (weight type 4)."""
    data = build_pmx_sdef(version, encoding)
    # Rewrite the single vertex's weight type byte from SDEF(3) to QDEF(4).
    # Locate the vertex weight type: offset of vertices after header+metadata.
    # Simpler: build a dedicated QDEF vertex block.
    enc_flag = 0 if encoding == "utf-16le" else 1
    out = bytearray()
    out += b"PMX " + struct.pack("<f", version)
    out += struct.pack("<B", 8)
    out += struct.pack("<B", enc_flag)
    out += struct.pack("<B", 0)
    for _ in range(6):
        out += struct.pack("<B", 1)
    out += _pack_str("synthetic", encoding)
    out += _pack_str("synthetic-en", encoding)
    out += _pack_str("synthetic comment", encoding)
    out += _pack_str("synthetic comment", encoding)
    out += struct.pack("<i", 1)          # 1 vertex
    out += struct.pack("<3f", 0, 0, 0)
    out += struct.pack("<3f", 0, 0, 1)
    out += struct.pack("<2f", 0, 0)
    out += struct.pack("<B", 4)          # QDEF
    out += struct.pack("<B", 0)
    out += struct.pack("<B", 1)
    out += struct.pack("<B", 0)
    out += struct.pack("<B", 1)
    out += struct.pack("<4f", 0.25, 0.25, 0.25, 0.25)  # 4 weights
    out += struct.pack("<f", 1.0)        # edge scale
    out += struct.pack("<i", 0)          # faces
    out += struct.pack("<i", 0)          # textures
    out += struct.pack("<i", 1)          # materials
    out += _pack_str("mat1", encoding)
    out += _pack_str("mat1", encoding)
    out += struct.pack("<4f", 1, 1, 1, 1)
    out += struct.pack("<3f", 0, 0, 0)
    out += struct.pack("<f", 0)
    out += struct.pack("<3f", 0, 0, 0)
    out += struct.pack("<B", 0)
    out += struct.pack("<4f", 0, 0, 0, 1)
    out += struct.pack("<f", 1.0)
    out += struct.pack("<i", -1)
    out += struct.pack("<i", -1)
    out += struct.pack("<B", 0)
    out += struct.pack("<B", 0)
    out += struct.pack("<B", 0)
    out += _pack_str("", encoding)
    out += struct.pack("<i", 3)
    out += struct.pack("<i", 0)          # bones
    out += struct.pack("<i", 0)          # morphs
    out += struct.pack("<i", 0)          # display frames
    out += struct.pack("<i", 0)          # rigid bodies
    out += struct.pack("<i", 0)          # joints
    return bytes(out)


def build_vmd_undecodable() -> bytes:
    """VMD whose model name contains a byte that is invalid CP932."""
    out = bytearray()
    out += b"Vocaloid Motion Data 0002" + b"\x00" * 5
    # model name: a CP932 lead byte 0x81 followed by 0x20 (not a valid trail
    # byte), so strict decode fails and the parser keeps "<hex:...>".
    name = b"test" + b"\x81\x20" + b"name"
    pad = 20 - len(name)
    if pad < 0:
        name = name[:20]
        pad = 0
    out += name + b"\x00" * pad
    out += struct.pack("<I", 0)   # bone
    out += struct.pack("<I", 0)   # morph
    out += struct.pack("<I", 0)   # camera
    out += struct.pack("<I", 0)   # light
    out += struct.pack("<I", 0)   # self shadow
    out += struct.pack("<I", 0)   # ik
    return bytes(out)


def build_vmd_ik() -> bytes:
    """VMD with one IK on/off frame (name 'legIK', enabled)."""
    out = bytearray()
    out += b"Vocaloid Motion Data 0002" + b"\x00" * 5
    out += "synthetic".encode("cp932").ljust(20, b"\x00")
    out += struct.pack("<I", 0)   # bone: 0
    out += struct.pack("<I", 0)   # morph: 0
    out += struct.pack("<I", 0)   # camera: 0
    out += struct.pack("<I", 0)   # light: 0
    out += struct.pack("<I", 0)   # self shadow: 0
    out += struct.pack("<I", 1)   # ik: 1 frame
    out += struct.pack("<I", 0)            # frame no
    out += struct.pack("<B", 1)            # show
    out += struct.pack("<I", 1)            # 1 ik name
    out += "legIK".encode("cp932").ljust(20, b"\x00")
    out += struct.pack("<B", 1)            # enabled
    return bytes(out)


def build_pmx_bone_features(version: float = 2.0, encoding: str = "utf-16le") -> bytes:
    """Minimal PMX exercising the bone tail / indexed-tail / IK payload branches.

    Three bones (no vertices/faces/materials so the bone walk is the focus):
      0 "center"  normal bone, tail = vec3
      1 "arm"     indexed tail (bit 0 set) -> tail = bone index 0
      2 "leg"     IK (bit 5 set) -> one IK link (no angle limits)

    This guards the tail-position regression: a spec-conformant PMX always
    carries a tail position (vec3 or bone index) after the bone flags, which
    the parser must consume before the next bone / IK payload.
    """
    enc_flag = 0 if encoding == "utf-16le" else 1
    out = bytearray()
    out += b"PMX " + struct.pack("<f", version)
    out += struct.pack("<B", 8)
    out += struct.pack("<B", enc_flag)
    out += struct.pack("<B", 0)          # additional uv
    for _ in range(6):
        out += struct.pack("<B", 1)      # index sizes
    out += _pack_str("synthetic", encoding)
    out += _pack_str("synthetic-en", encoding)
    out += _pack_str("synthetic comment", encoding)
    out += _pack_str("synthetic comment", encoding)
    out += struct.pack("<i", 0)          # vertices
    out += struct.pack("<i", 0)          # faces
    out += struct.pack("<i", 0)          # textures
    out += struct.pack("<i", 0)          # materials
    out += struct.pack("<i", 3)          # bones

    def bone(name, pos, parent, flag, extra=b""):
        nonlocal out
        out += _pack_str(name, encoding)
        out += _pack_str(name, encoding)
        out += struct.pack("<3f", *pos)
        out += struct.pack("<B", parent)
        out += struct.pack("<i", 0)      # layer
        out += struct.pack("<H", flag)
        out += extra

    # bone 0: normal, tail = vec3 (0,1,0)
    bone("center", (0, 0, 0), 0, 0x0008 | 0x0002 | 0x0004,
         struct.pack("<3f", 0, 1, 0))
    # bone 1: indexed tail (bit 0) -> tail = bone index 0
    bone("arm", (0, 1, 0), 0, 0x0008 | 0x0002 | 0x0004 | 0x0001,
         struct.pack("<B", 0))
    # bone 2: IK (bit 5), one link without angle limits
    ik = (struct.pack("<B", 2) +         # IK target bone index
          struct.pack("<i", 10) +        # loop count
          struct.pack("<f", 0.5) +       # limit radian
          struct.pack("<i", 1) +         # link count
          struct.pack("<B", 0) +         # link bone index
          struct.pack("<B", 0))          # has limits = 0
    bone("leg", (0, 2, 0), 0, 0x0008 | 0x0002 | 0x0004 | 0x0020,
         struct.pack("<3f", 0, 1, 0) + ik)  # tail vec3 + IK payload

    out += struct.pack("<i", 0)          # morphs
    out += struct.pack("<i", 0)          # display frames
    out += struct.pack("<i", 0)          # rigid bodies
    out += struct.pack("<i", 0)          # joints
    return bytes(out)


def main() -> None:
    # PMX samples — these are the synthetic inputs (do NOT commit real assets).
    samples = {
        "pmx20_utf16le.pmx": build_pmx_v2(2.0, "utf-16le"),
        "pmx21_utf8.pmx": build_pmx_v2(2.1, "utf-8"),
        "motion.vmd": build_vmd(),
    }
    for name, data in samples.items():
        p = os.path.join(SAMPLES, name)
        with open(p, "wb") as fh:
            fh.write(data)
        print("wrote %s (%d bytes)" % (name, len(data)))

    # Golden JSON: hand-authored expected parse results (not derived from the
    # parser — they encode the known values the synthetic builders emit).
    _bone0 = {"name": "center", "name_en": "center", "position": (0.0, 0.0, 0.0),
              "parent_index": 0, "flag": 14}
    _bone1 = {"name": "arm", "name_en": "arm", "position": (0.0, 0.0, 0.0),
              "parent_index": 0, "flag": 14}
    _mat = {"name": "mat1", "diffuse": (1.0, 1.0, 1.0, 1.0),
            "ambient": (0.0, 0.0, 0.0), "face_count": 3, "toon_flag": 0}
    _morph = {"name": "smile", "type": 1,
              "offsets": [{"vertex_index": 0, "offset": (0.0, 0.1, 0.0)}]}
    golden_pmx20 = {
        "ir_version": "0.2.0", "format": "pmx", "model_name": "synthetic",
        "pmx_version": 2.0, "encoding": "utf-16le",
        "bones": [_bone0, _bone1], "morphs": [_morph], "materials": [_mat],
        "counts_materials": 1, "counts_bones": 2, "counts_morphs": 1,
        "counts_vertices": 1, "counts_surfaces": 1,
        "counts_rigid_bodies": 0, "counts_joints": 0,
    }
    golden_pmx21 = dict(golden_pmx20)
    golden_pmx21.update({"pmx_version": 2.1, "encoding": "utf-8"})
    golden_vmd = {
        "ir_version": "0.2.0", "format": "vmd", "model_name": "synthetic",
        "bones": [
            {"name": "center", "frame": 0, "position": (0.0, 0.0, 0.0),
             "rotation": (0.0, 0.0, 0.0, 1.0)},
            {"name": "arm", "frame": 30, "position": (0.0, 0.0, 0.0),
             "rotation": (0.0, 0.0, 0.0, 1.0)},
        ],
        "cameras": [
            {"frame": 0, "distance": 10.0, "fov": 30, "perspective": True,
             "position": (0.0, 5.0, -10.0)},
            {"frame": 30, "distance": 10.0, "fov": 30, "perspective": True,
             "position": (0.0, 5.0, -10.0)},
        ],
        "bone_frames": 2, "morph_frames": 1, "camera_frames": 2,
        "light_frames": 0, "self_shadow_frames": 0, "ik_frames": 0,
    }

    goldens = {
        "golden_pmx20_utf16le.json": golden_pmx20,
        "golden_pmx21_utf8.json": golden_pmx21,
        "golden_vmd.json": golden_vmd,
    }
    for name, data in goldens.items():
        p = os.path.join(GOLDEN, name)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print("wrote %s" % name)


if __name__ == "__main__":
    main()
