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
        # no target/ik/etc flag => nothing after flag
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
        "ir_version": "0.1.0", "format": "pmx", "model_name": "synthetic",
        "pmx_version": 2.0, "encoding": "utf-16le",
        "bones": [_bone0, _bone1], "morphs": [_morph], "materials": [_mat],
        "counts_materials": 1, "counts_bones": 2, "counts_morphs": 1,
        "counts_vertices": 1, "counts_surfaces": 1,
        "counts_rigid_bodies": 0, "counts_joints": 0,
    }
    golden_pmx21 = dict(golden_pmx20)
    golden_pmx21.update({"pmx_version": 2.1, "encoding": "utf-8"})
    golden_vmd = {
        "ir_version": "0.1.0", "format": "vmd", "model_name": "synthetic",
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
