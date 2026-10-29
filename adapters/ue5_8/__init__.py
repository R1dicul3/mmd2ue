"""MMD2UE UE 5.8 adapter layer (adapters/ue5_8/).

These scripts run INSIDE Unreal Engine 5.8 (via the Python editor /
commandlet). They consume the glTF exported by the core layer and drive
UE native import to build a SkeletalMesh. This is the only place that may
``import unreal`` (constraints C1/C2, ADR-001 core/adapter separation).

The core layer (src/mmd2ue/core/) never imports unreal; the adapter only
consumes glTF files, never the core IR internals (constraint C2).

Zero asset distribution (ADR-006): these scripts are pure import logic;
they reference the local glTF and texture files, never bundling any
PMX/VMD/model assets.
"""

from . import import_gltf, material_map

__all__ = ["import_gltf", "material_map"]
