"""Unit tests for the IR module and version gating (AC-M1-5)."""

from __future__ import annotations

import pytest

from mmd2ue.core.ir import (
    IR_VERSION,
    ModelIR,
    MotionIR,
    require_ir_version,
)


def test_ir_version_string():
    assert isinstance(IR_VERSION, str)
    assert IR_VERSION.count(".") >= 1


def test_model_ir_defaults():
    ir = ModelIR()
    assert ir.ir_version == IR_VERSION
    assert ir.format == "pmx"
    assert ir.rigid_bodies == []
    assert ir.joints == []


def test_model_ir_to_dict_has_version():
    d = ModelIR().to_dict()
    assert d["ir_version"] == IR_VERSION


def test_motion_ir_to_dict_has_version():
    d = MotionIR().to_dict()
    assert d["ir_version"] == IR_VERSION


def test_require_ir_version_ok():
    require_ir_version({"ir_version": IR_VERSION})


def test_require_ir_version_mismatch_rejects():
    with pytest.raises(ValueError):
        require_ir_version({"ir_version": "0.0.0"})


def test_require_ir_version_missing_rejects():
    with pytest.raises(ValueError):
        require_ir_version({})
