"""UE 5.8 adapter: import a glTF file into a SkeletalMesh (D-M2-2, D-M2-3).

Runs inside Unreal Engine (only here `import unreal` is permitted -
constraints C1/C2, ADR-001). Consumes the glTF produced by the core
exporter. Two stages:
  1. import the glTF through the UE native Interchange glTF import to
     produce a SkeletalMesh + Skeleton (bone names preserved end-to-end);
  2. read the glTF materials and create one MaterialInstanceConstant per
     glTF material (parent = MMD-approximation master material, with
     BaseColor / BaseColorTexture set), then assign those instances to the
     SkeletalMesh material slots (FSkeletalMaterial).

Commandlet smoke path: see ``run_commandlet_smoke`` and module docstring.

IMPORTANT (unverified status): this adapter is authored against the UE 5.x
Python API and has NOT been executed inside a real Unreal 5.8 editor. The
exact class/property names (GltfImportOptions, Interchange asset task,
FSkeletalMaterial construction) must be confirmed against the target UE
5.8 Python stubs before production use. See docs/stage2-requirements.md
and the M2 acceptance note (AC-M2-1..3 are bound to a live UE run).
"""

from __future__ import annotations

import json
import os
from typing import Optional

try:
    import unreal  # noqa: F401  (UE-only adapter layer, constraint C1)
except ImportError:  # pragma: no cover - only raised outside UE
    unreal = None

try:
    from . import material_map  # package context (adapters.ue5_8)
except ImportError:  # flat import (UE Python / tests)
    import material_map  # noqa: E402


# Master material path (D-M2-3): the single shared parent material.
MMD_MASTER_MATERIAL = "/Game/MMD2UE/M_MMD_Approximation"


def _read_gltf_materials(gltf_path: str) -> list:
    """Read the glTF JSON materials array (list of dicts).

    Works without unreal (pure json), so the mapping logic is unit-
    testable and shared with the core exporter report semantics.
    """
    with open(gltf_path, encoding="utf-8") as fh:
        gltf = json.load(fh)
    materials = gltf.get("materials", [])
    images = gltf.get("images", [])
    textures = gltf.get("textures", [])
    result = []
    for idx, mat in enumerate(materials):
        pbr = mat.get("pbrMetallicRoughness", {})
        base_color = pbr.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0])
        texture_uri = None
        bct = pbr.get("baseColorTexture")
        if bct is not None:
            tex = textures[bct.get("index", 0)]
            src = images[tex.get("source", 0)]
            texture_uri = src.get("uri")
        result.append({
            "name": mat.get("name", "mat_%d" % idx),
            "base_color": base_color,
            "texture_uri": texture_uri,
        })
    return result


def import_gltf_to_skeletal_mesh(
        gltf_path: str,
        destination_path: str = "/Game/Imported/",
        asset_name=None,
        import_skeleton: bool = True,
        import_material: bool = True):
    """Import a glTF file into a SkeletalMesh plus per-material instances.

    Uses the UE native glTF import (Interchange / GltfImportFactory) so
    bone names and skin weights come through the supported import chain
    (ADR-007, v1). Then reads the glTF materials and creates one
    MaterialInstanceConstant per material (D-M2-3) and assigns them to
    the mesh material slots.

    Returns the SkeletalMesh, or None on failure / when unreal is absent.
    """
    if unreal is None:
        return None

    if not os.path.isfile(gltf_path):
        unreal.log_error("glTF not found: %s" % gltf_path)
        return None

    name = asset_name or os.path.splitext(os.path.basename(gltf_path))[0]

    # Stage 1: import via the glTF factory (Interchange) - UNVERIFIED names.
    task = unreal.AssetImportTask()
    task.filename = os.path.abspath(gltf_path)
    task.destination_path = destination_path
    task.destination_name = name
    task.replace_existing = True
    task.automated = True
    task.save = True

    factory = unreal.GltfImportFactory()
    task.factory = factory

    options = unreal.GltfImportOptions()
    options.import_skeleton = import_skeleton
    options.import_material = import_material
    factory.set_editor_property("settings", options)
    task.options = options

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    skeletal_mesh = None
    for imported in (task.get_editor_property("imported_object_paths") or []):
        asset = unreal.load_asset(imported)
        if isinstance(asset, unreal.SkeletalMesh):
            skeletal_mesh = asset
            break

    if skeletal_mesh is None:
        unreal.log_error("glTF import produced no SkeletalMesh: %s" % gltf_path)
        return None

    unreal.log("Imported SkeletalMesh: %s" % skeletal_mesh.get_path_name())

    # Stage 2: per-material MaterialInstanceConstant + slot assignment.
    materials = _read_gltf_materials(gltf_path)
    instances = material_map.create_material_instances_from_gltf(
        materials, destination_path, name)
    material_map.assign_materials_to_skeletal_mesh(
        skeletal_mesh, instances)

    return skeletal_mesh


def import_gltf(gltf_path: str, destination_path: str = "/Game/Imported/"):
    """Convenience wrapper: import glTF -> SkeletalMesh (public API)."""
    return import_gltf_to_skeletal_mesh(gltf_path, destination_path)


def run_commandlet_smoke():
    """Commandlet smoke path for downstream UE-side verification.

    Intended to run inside an UE Python commandlet / editor Python console:
      py import adapters.ue5_8.import_gltf as ig
      py ig.run_commandlet_smoke()
    Expected log (success):
      LogPython: [mmd2ue] importing /path/model.gltf
      LogPython: Imported SkeletalMesh: /Game/Imported/model
      LogPython: [mmd2ue] assigned N material instance(s)
    """
    gltf_path = os.environ.get("MMD2UE_GLTF")
    if not gltf_path:
        print("[mmd2ue] usage: set MMD2UE_GLTF=/path/model.gltf then rerun")
        return None
    print("[mmd2ue] importing %s" % gltf_path)
    mesh = import_gltf_to_skeletal_mesh(gltf_path)
    if mesh is None:
        print("[mmd2ue] import failed")
    return mesh

