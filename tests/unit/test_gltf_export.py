"""Unit tests for the core glTF exporter (no real assets, no unreal)."""

from __future__ import annotations

import inspect
import json
import os

from conftest import sample_bytes

from mmd2ue.core.ir import ModelIR, Vertex
from mmd2ue.core.parsers import pmx
from mmd2ue.core.export import gltf
from mmd2ue.core.export.gltf import ExportReport, GLTF_VERSION


def test_export_gltf_returns_triple():
    ir = pmx.parse(sample_bytes("pmx20_utf16le.pmx"))
    g, bin_data, report = gltf.export_gltf(ir)
    assert isinstance(g, dict)
    assert isinstance(bin_data, bytes)
    assert isinstance(report, ExportReport)
    assert g["asset"]["version"] == GLTF_VERSION


def test_export_gltf_preserves_material_name():
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g, _bin_data, _report = gltf.export_gltf(ir)
    assert g["materials"][0]["name"] == "skin"


def test_export_gltf_sdef_approximated_as_bdef2():
    ir = pmx.parse(sample_bytes("pmx_sdef.pmx"))
    g, _bin_data, report = gltf.export_gltf(ir)
    assert report.sdef_approximated == 1
    prim = g["meshes"][0]["primitives"][0]
    w_acc = g["accessors"][prim["attributes"]["WEIGHTS_0"]]
    assert w_acc["count"] == 1


def test_export_gltf_deterministic():
    a = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    b = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g1, bin1, _ = gltf.export_gltf(a)
    g2, bin2, _ = gltf.export_gltf(b)
    assert json.dumps(g1, sort_keys=True) == json.dumps(g2, sort_keys=True)
    assert bin1 == bin2


def test_export_gltf_no_unreal_import():
    src = inspect.getsource(gltf)
    assert "import unreal" not in src
    assert "unreal." not in src


def test_export_gltf_report_ignored_materials():
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    _g, _bin_data, report = gltf.export_gltf(ir)
    d = report.to_dict()
    assert len(d["ignored_materials"]) == 1
    items = d["ignored_materials"][0]["items"]
    assert set(items) == {"sphere_map", "toon", "edge"}


def test_export_gltf_has_buffer_uri():
    """F1: buffers[0] carries a uri (external .bin)."""
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g, _bin_data, _report = gltf.export_gltf(ir)
    assert g["buffers"][0]["uri"]


def test_export_gltf_files_writes_bin_and_uri(tmp_path):
    """F1: export_gltf_files writes .bin and sets uri to the bin basename."""
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    gltf_path = str(tmp_path / "m.gltf")
    bin_path = str(tmp_path / "m.bin")
    report = gltf.export_gltf_files(ir, gltf_path, bin_path)
    assert os.path.isfile(gltf_path)
    assert os.path.isfile(bin_path)
    with open(gltf_path, encoding="utf-8") as fh:
        g = json.load(fh)
    assert g["buffers"][0]["uri"] == "m.bin"
    # The uri basename points at the actual .bin file that exists next to it.
    with open(os.path.join(str(tmp_path), g["buffers"][0]["uri"]), "rb") as fh:
        data = fh.read()
    assert len(data) == g["buffers"][0]["byteLength"]
    assert len(data) > 0
    assert report is not None


def test_export_gltf_report_canonical_keys():
    """F3: report lists units/skipped/approximated."""
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    _g, _bin_data, report = gltf.export_gltf(ir)
    d = report.to_dict()
    for key in ("units", "skipped", "approximated"):
        assert key in d


def test_export_gltf_position_min_max():
    """F4: POSITION accessor has min/max."""
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    g, _bin_data, _report = gltf.export_gltf(ir)
    prim = g["meshes"][0]["primitives"][0]
    pos = g["accessors"][prim["attributes"]["POSITION"]]
    assert "min" in pos and "max" in pos


def test_export_gltf_report_texture_refs():
    """F7: report lists external texture refs (material -> uri)."""
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    _g, _bin_data, report = gltf.export_gltf(ir)
    refs = report.to_dict()["texture_refs"]
    assert refs == [{"material_index": 0, "name": "skin", "texture_uri": "diffuse.png"}]


def test_export_gltf_minimal_material_dict():
    """F10: a material dict with only name/diffuse exports without KeyError."""
    ir = ModelIR()
    ir.bones = [{"name": "root", "position": (0.0, 0.0, 0.0), "parent_index": -1}]
    ir.vertices = [Vertex(position=(0.0, 0.0, 0.0), joints=[0], weights=[1.0])]
    ir.faces = [0, 0, 0]
    # Minimal material: only name + diffuse (no texture_index/sphere/toon/edge).
    ir.materials = [{"name": "min", "diffuse": (0.2, 0.3, 0.4, 1.0)}]
    g, _bin_data, report = gltf.export_gltf(ir)
    assert g["materials"][0]["name"] == "min"
    bc = g["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"]
    assert [round(v, 3) for v in bc] == [0.2, 0.3, 0.4, 1.0]
    # no texture -> no baseColorTexture, no texture_refs
    assert "baseColorTexture" not in g["materials"][0]["pbrMetallicRoughness"]
    assert report.to_dict()["texture_refs"] == []


def test_export_gltf_minimal_material_missing_all_optional_keys():
    """F10: a material dict with no optional keys at all still exports."""
    ir = ModelIR()
    ir.bones = []
    ir.vertices = [Vertex(position=(0.0, 0.0, 0.0))]
    ir.faces = []
    ir.materials = [{"name": "bare"}]  # no diffuse, no texture_index, nothing
    g, _bin_data, _report = gltf.export_gltf(ir)
    assert g["materials"][0]["name"] == "bare"
    bc = g["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"]
    assert [round(v, 3) for v in bc] == [1.0, 1.0, 1.0, 1.0]  # default white


def test_export_gltf_joints_0_upgrades_beyond_256_bones():
    """F8-low: JOINTS_0 uses UNSIGNED_SHORT when bone count exceeds 256."""
    ir = ModelIR()
    # 300 bones so the max joint index (299) exceeds UNSIGNED_BYTE's 255.
    ir.bones = [{"name": "b%d" % i, "position": (0.0, 0.0, 0.0),
                 "parent_index": -1} for i in range(300)]
    ir.vertices = [Vertex(position=(0.0, 0.0, 0.0), joints=[299], weights=[1.0])]
    ir.faces = []
    g, _bin_data, _report = gltf.export_gltf(ir)
    prim = g["meshes"][0]["primitives"][0]
    joints_acc = g["accessors"][prim["attributes"]["JOINTS_0"]]
    assert joints_acc["componentType"] == 5123  # UNSIGNED_SHORT


def test_export_gltf_joints_0_uses_byte_for_small_models():
    """F8-low: JOINTS_0 stays UNSIGNED_BYTE for <= 256 bones."""
    ir = ModelIR()
    ir.bones = [{"name": "b%d" % i, "position": (0.0, 0.0, 0.0),
                 "parent_index": -1} for i in range(2)]
    ir.vertices = [Vertex(position=(0.0, 0.0, 0.0), joints=[1], weights=[1.0])]
    ir.faces = []
    g, _bin_data, _report = gltf.export_gltf(ir)
    prim = g["meshes"][0]["primitives"][0]
    joints_acc = g["accessors"][prim["attributes"]["JOINTS_0"]]
    assert joints_acc["componentType"] == 5121  # UNSIGNED_BYTE

