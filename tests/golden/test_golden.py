"""Golden comparison: parser output vs. hand-authored golden IR JSON.

Golden files encode the manually-specified expected parse results for the
synthetic samples (AC-M1-3). Parser output is normalized to the same shape
before comparison. Synthetic sample bytes come from conftest (tools/gen_samples).
"""

from __future__ import annotations

import json
import os

from conftest import sample_bytes

from mmd2ue.core.parsers import pmx, vmd

HERE = os.path.dirname(os.path.abspath(__file__))


def _read_json(name: str) -> dict:
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return json.load(fh)


def _round3(t):
    return [round(x, 3) for x in t]


def _normalize_pmx(ir) -> dict:
    c = ir.counts
    # Deep coverage of the key per-element fields required by R2: bone
    # name/name_en/position/parent_index/flag, material diffuse/ambient/
    # face_count/toon_flag, morph type + offsets.
    bones = [
        {"name": b["name"], "name_en": b["name_en"], "position": _round3(b["position"]),
         "parent_index": b["parent_index"], "flag": b["flag"]}
        for b in ir.bones
    ]
    morphs = [
        {"name": m["name"], "type": m["type"],
         "offsets": [{"vertex_index": o.get("vertex_index", 0),
                       "offset": _round3(o["offset"])}
                      for o in m["offsets"]]}
        for m in ir.morphs
    ]
    mats = [
        {"name": m["name"], "diffuse": _round3(m["diffuse"]),
         "ambient": _round3(m["ambient"]), "face_count": m["face_count"],
         "toon_flag": m["toon_flag"]}
        for m in ir.materials
    ]
    return {
        "ir_version": ir.ir_version,
        "format": ir.format,
        "model_name": ir.model_name,
        "pmx_version": round(ir.pmx_version, 1),
        "encoding": ir.encoding,
        "bones": bones,
        "morphs": morphs,
        "materials": mats,
        "counts_materials": c["materials"],
        "counts_bones": c["bones"],
        "counts_morphs": c["morphs"],
        "counts_vertices": c["vertices"],
        "counts_surfaces": c["surfaces"],
        "counts_rigid_bodies": c["rigid_bodies"],
        "counts_joints": c["joints"],
    }


def _normalize_vmd(ir) -> dict:
    bones = [
        {"name": b["name"], "frame": b["frame"],
         "position": _round3(b["position"]), "rotation": _round3(b["rotation"])}
        for b in ir.bone_frames
    ]
    cams = [
        {"frame": c["frame"], "distance": round(c["distance"], 3),
         "fov": c["fov"], "perspective": c["perspective"],
         "position": _round3(c["position"])}
        for c in ir.camera_frames
    ]
    return {
        "ir_version": ir.ir_version,
        "format": ir.format,
        "model_name": ir.model_name,
        "bones": bones,
        "cameras": cams,
        "bone_frames": len(ir.bone_frames),
        "morph_frames": len(ir.morph_frames),
        "camera_frames": len(ir.camera_frames),
        "light_frames": len(ir.light_frames),
        "self_shadow_frames": len(ir.self_shadow_frames),
        "ik_frames": len(ir.ik_frames),
    }


def test_golden_pmx20_utf16le():
    ir = pmx.parse(sample_bytes("pmx20_utf16le.pmx"))
    assert _normalize_pmx(ir) == _read_json("golden_pmx20_utf16le.json")


def test_golden_pmx21_utf8():
    ir = pmx.parse(sample_bytes("pmx21_utf8.pmx"))
    assert _normalize_pmx(ir) == _read_json("golden_pmx21_utf8.json")


def test_golden_vmd():
    ir = vmd.parse(sample_bytes("motion.vmd"))
    assert _normalize_vmd(ir) == _read_json("golden_vmd.json")
