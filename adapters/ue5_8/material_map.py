"""UE 5.8 adapter: MMD-approximation material mapping (D-M2-3).

Implements docs/stage2-requirements.md section 3: each PMX material maps
to one UE MaterialInstanceConstant whose parent is a single shared
MMD-approximation master material. Mapping rules:

  diffuse RGB(a)           -> BaseColor vector parameter
  texture (diffuse map)    -> BaseColorTexture texture parameter
  sphere map / toon / edge -> ignored in v1 (recorded by the core exporter
    report; the adapter does not create per-feature params)

Only here may import unreal appear (constraint C1). The core exporter
already recorded the ignored sphere/toon/edge items in its glTF export
report; this adapter only establishes the master material + per-material
instances (D-M2-3) and assigns them to SkeletalMesh slots.

UNVERIFIED status: authored against the UE 5.x Python API; not executed
inside a live Unreal 5.8 editor. FSkeletalMaterial construction and the
exact editor-property names must be confirmed on the target 5.8 build.
"""

from __future__ import annotations

from typing import Optional

try:
    import unreal  # noqa: F401  (UE-only adapter layer, constraint C1)
except ImportError:  # pragma: no cover
    unreal = None


# The single shared master material asset path (D-M2-3).
MMD_MASTER_MATERIAL_PATH = "/Game/MMD2UE/M_MMD_Approximation"
MMD_MASTER_MATERIAL_LABEL = "M_MMD_Approximation"

BASE_PARENT_PATH = None  # None -> engine default material if needed


def ensure_mmd_master_material():
    """Return (creating if needed) the single MMD-approximation master.

    Returns None when unreal is unavailable (static checks outside UE).
    """
    if unreal is None:
        return None

    asset = unreal.load_asset(MMD_MASTER_MATERIAL_PATH)
    if asset is not None:
        return asset

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.MaterialFactoryNew()
    asset = asset_tools.create_asset(
        MMD_MASTER_MATERIAL_LABEL,
        os_dirname(MMD_MASTER_MATERIAL_PATH),
        unreal.Material,
        factory,
    )
    if asset is not None:
        unreal.EditorAssetLibrary.save_asset(
            MMD_MASTER_MATERIAL_PATH, only_if_is_dirty=False)
    return asset


def create_material_instances_from_gltf(
        materials, package_path: str, asset_base: str):
    """Create one MaterialInstanceConstant per glTF material (D-M2-3).

    materials is the list of dicts from import_gltf._read_gltf_materials;
    each has name (str), base_color (RGBA list), texture_uri (str or None).
    Returns a list of MaterialInstanceConstant (one per slot), or [] when
    unreal is absent.
    """
    if unreal is None:
        return []

    instances = []
    for idx, mat in enumerate(materials):
        name = "%s_mat%d" % (asset_base, idx)
        mi = create_material_instance(
            package_path, name, mat.get("base_color"), mat.get("texture_uri"))
        if mi is not None:
            instances.append(mi)
        else:
            instances.append(None)
    return instances


def create_material_instance(
        package_path: str,
        name: str,
        base_color,
        texture_path=None):
    """Create one MaterialInstanceConstant (parent = master material)."""
    if unreal is None:
        return None

    master = ensure_mmd_master_material()
    if master is None:
        return None

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    mi = asset_tools.create_asset(
        name, package_path, unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew(),
    )
    if mi is None:
        return None

    mi.set_editor_property("parent", master)
    if base_color is not None:
        bc = unreal.LinearColor(
            r=float(base_color[0]),
            g=float(base_color[1]),
            b=float(base_color[2]),
            a=float(base_color[3]) if len(base_color) > 3 else 1.0,
        )
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
            mi, "BaseColor", bc)
    if texture_path:
        tex = unreal.load_asset(texture_path)
        if tex is not None:
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                mi, "BaseColorTexture", tex)
    unreal.MaterialEditingLibrary.recompile_material_instance(mi)
    unreal.EditorAssetLibrary.save_loaded_asset(mi)
    return mi


def assign_materials_to_skeletal_mesh(skeletal_mesh, instances) -> None:
    """Assign per-material MaterialInstanceConstant to the mesh slots.

    A SkeletalMesh material slot is an FSkeletalMaterial (binds a
    UMaterialInterface + slot name), not a bare UMaterial list. We build
    one FSkeletalMaterial per instance; slots with no instance fall back
    to the master material.
    """
    if unreal is None or skeletal_mesh is None:
        return

    master = ensure_mmd_master_material()
    slots = []
    for inst in instances:
        mat = inst if inst is not None else master
        if mat is None:
            continue
        slot = unreal.SkeletalMaterial()
        slot.material_interface = mat
        slot.material_slot_name = "MMD_%d" % len(slots)
        slots.append(slot)
    if slots:
        skeletal_mesh.set_editor_property("materials", slots)
        unreal.log("[mmd2ue] assigned %d material instance(s)" % len(slots))
    else:
        unreal.log("[mmd2ue] no material instances to assign")


def os_dirname(path: str) -> str:
    """Return the package directory (parent) of an asset path."""
    idx = path.rfind("/")
    return path[:idx] if idx > 0 else "/Game"
