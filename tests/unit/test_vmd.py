"""Unit tests for the VMD parser (synthetic samples only)."""

from __future__ import annotations

import pytest

from mmd2ue.core.ir import MotionIR, IR_VERSION
from mmd2ue.core.parsers import vmd
from mmd2ue.core.parsers.vmd import ParserError
from conftest import sample_bytes


def test_vmd_counts_and_cp932():
    ir = vmd.parse(sample_bytes("motion.vmd"))
    assert isinstance(ir, MotionIR)
    assert ir.ir_version == IR_VERSION
    assert ir.model_name == "synthetic"
    assert len(ir.bone_frames) == 2
    assert len(ir.morph_frames) == 1
    assert len(ir.camera_frames) == 2
    assert len(ir.light_frames) == 0
    assert len(ir.self_shadow_frames) == 0
    assert len(ir.ik_frames) == 0


def test_bone_frames_sorted_by_frame():
    ir = vmd.parse(sample_bytes("motion.vmd"))
    frames = [f["frame"] for f in ir.bone_frames]
    assert frames == sorted(frames)


def test_cp932_japanese_name():
    name = "テスト".encode("cp932")
    data = b"Vocaloid Motion Data 0002" + b"\x00" * 5
    data += name.ljust(20, b"\x00")
    for _ in range(6):
        data += b"\x00" * 4
    ir = vmd.parse(data)
    assert ir.model_name == "テスト"


def test_bad_signature_raises():
    with pytest.raises(ParserError):
        vmd.parse(b"not a vmd" + b"\x00" * 64)


def test_undecodable_name_counts_approximated():
    ir = vmd.parse(sample_bytes("vmd_undecodable.vmd"))
    assert ir.model_name.startswith("<hex:")
    assert ir.report["approximated"] == 1
    assert ir.report["skipped"] == 0


def test_ik_frame_parsed():
    ir = vmd.parse(sample_bytes("vmd_ik.vmd"))
    assert len(ir.ik_frames) == 1
    assert ir.ik_frames[0]["ik"][0]["name"] == "legIK"
    assert ir.ik_frames[0]["ik"][0]["enabled"] is True


def test_no_unreal_import():
    import inspect
    assert "import unreal" not in inspect.getsource(vmd)
