"""Unit tests for the UE adapter layer (no real UE, no real assets).

Verifies the pure-JSON parts of the adapter (glTF material parsing) and
that the adapter imports cleanly without unreal (returns None gracefully).
"""

from __future__ import annotations

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADAPTERS = os.path.join(ROOT, "adapters", "ue5_8")
if ADAPTERS not in sys.path:
    sys.path.insert(0, ADAPTERS)

from conftest import sample_bytes

from mmd2ue.core.parsers import pmx
from mmd2ue.core.export import gltf

import import_gltf
import material_map


def test_adapter_imports_without_unreal():
    """F6: adapter module is importable outside UE (import unreal guarded)."""
    assert import_gltf.unreal is None
    assert material_map.unreal is None
    assert import_gltf.import_gltf("x.gltf") is None
    assert material_map.ensure_mmd_master_material() is None


def test_read_gltf_materials_parses_material_and_texture(tmp_path):
    """F6: _read_gltf_materials maps glTF material -> base_color + texture_uri."""
    ir = pmx.parse(sample_bytes("pmx_gltf.pmx"))
    gltf_path = str(tmp_path / "m.gltf")
    with open(gltf_path, "w", encoding="utf-8") as fh:
        fh.write(gltf.export_gltf_json(ir))
    mats = import_gltf._read_gltf_materials(gltf_path)
    assert len(mats) == 1
    assert mats[0]["name"] == "skin"
    assert [round(v, 3) for v in mats[0]["base_color"][:3]] == [0.8, 0.6, 0.4]
    assert mats[0]["texture_uri"] == "diffuse.png"


def test_adapter_has_commandlet_smoke():
    """F6: commandlet smoke entry point exists and is callable."""
    assert callable(import_gltf.run_commandlet_smoke)
