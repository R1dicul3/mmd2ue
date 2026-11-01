"""Unit tests for the PMX parser (synthetic samples only, no real assets)."""

from __future__ import annotations

import pytest

from mmd2ue.core.ir import ModelIR, IR_VERSION
from mmd2ue.core.parsers import pmx
from mmd2ue.core.parsers.pmx import ParserError
from conftest import sample_bytes


def test_pmx20_utf16le_counts():
    ir = pmx.parse(sample_bytes("pmx20_utf16le.pmx"))
    assert isinstance(ir, ModelIR)
    assert ir.ir_version == IR_VERSION
    assert ir.pmx_version == 2.0
    assert ir.encoding == "utf-16le"
    assert ir.model_name == "synthetic"
    assert ir.counts["bones"] == 2
    assert ir.counts["materials"] == 1
    assert ir.counts["morphs"] == 1
    assert ir.counts["vertices"] == 1


def test_pmx21_utf8_counts():
    ir = pmx.parse(sample_bytes("pmx21_utf8.pmx"))
    assert ir.encoding == "utf-8"
    assert abs(ir.pmx_version - 2.1) < 0.001
    assert ir.counts["bones"] == 2
    assert ir.counts["materials"] == 1
    assert ir.counts["morphs"] == 1


def test_bad_signature_raises():
    with pytest.raises(ParserError):
        pmx.parse(b"XXXX" + b"\x00" * 100)


def test_unknown_version_raises():
    data = b"PMX " + b"\x00\x00\x80?" + b"\x00" * 64
    with pytest.raises(ParserError):
        pmx.parse(data)


def test_material_payload_present():
    ir = pmx.parse(sample_bytes("pmx20_utf16le.pmx"))
    assert len(ir.materials) == 1
    m = ir.materials[0]
    assert m["name"] == "mat1"
    assert m["face_count"] == 3


def test_sdef_vertex_counts_approximated():
    ir = pmx.parse(sample_bytes("pmx_sdef.pmx"))
    assert ir.counts["vertices"] == 1
    assert ir.report["approximated"] == 1
    assert ir.report["skipped"] == 0


def test_qdef_vertex_counts_skipped():
    ir = pmx.parse(sample_bytes("pmx_qdef.pmx"))
    assert ir.counts["vertices"] == 1
    assert ir.report["skipped"] == 1
    assert ir.report["approximated"] == 0


def test_report_units_one_model():
    """F9: PMX report units = 1 (one model per file), not vertex count."""
    ir = pmx.parse(sample_bytes("pmx20_utf16le.pmx"))
    assert ir.report["units"] == 1


def test_no_unreal_import():
    import inspect
    assert "import unreal" not in inspect.getsource(pmx)


def test_bone_tail_position_vec3_and_indexed_tail():
    """Tail position is always present: vec3 normally, bone index when bit 0 set.

    Guards the tail-position regression: the parser must consume the tail
    payload before the next bone so a real PMX does not desynchronise.
    """
    ir = pmx.parse(sample_bytes("pmx_bone_features.pmx"))
    assert ir.counts["bones"] == 3
    b0, b1, b2 = ir.bones
    # Bone 0: normal tail -> vec3.
    assert b0["tail_index"] is None
    assert b0["tail_position"] == (0.0, 1.0, 0.0)
    # Bone 1: indexed tail (bit 0) -> bone index 0, no vec3.
    assert b1["tail_index"] == 0
    assert b1["tail_position"] is None
    # Bone 2: normal tail (vec3) even though it also has IK.
    assert b2["tail_position"] == (0.0, 1.0, 0.0)
    assert b2["tail_index"] is None


def test_bone_ik_payload():
    """IK (bit 5) is the last bone field and is parsed correctly."""
    ir = pmx.parse(sample_bytes("pmx_bone_features.pmx"))
    leg = ir.bones[2]
    assert leg["ik"] is not None
    assert leg["ik"]["target"] == 2
    assert leg["ik"]["loop"] == 10
    assert abs(leg["ik"]["limit_rad"] - 0.5) < 1e-6
    assert len(leg["ik"]["links"]) == 1
    link = leg["ik"]["links"][0]
    assert link["target"] == 0
    assert link["has_limit"] is False
    assert link["limit_min"] is None
    assert link["limit_max"] is None
    # Bones without IK have ik=None.
    assert ir.bones[0]["ik"] is None
