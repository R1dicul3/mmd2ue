"""Core glTF 2.0 exporter: model IR -> glTF 2.0 (.gltf + .bin).

Pure standard library, no UE / unreal dependency (constraints C1/C2/C3).
Follows ADR-007 (intermediate glTF path, v1).
"""

from mmd2ue.core.export import gltf

__all__ = ["gltf"]
