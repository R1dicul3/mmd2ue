"""Intermediate Representation (IR) data structures.

The IR is the single source of truth shared between the core parsers and the
future UE adaptation layer (adapters/ue5_8/). Every produced artifact carries
an ir_version; loading refuses a mismatched version (no implicit compatibility).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

IR_VERSION = "0.1.0"


@dataclass
class Bone:
    name: str
    name_en: str = ""
    position: tuple = (0.0, 0.0, 0.0)
    parent_index: int = -1
    layer: int = 0
    flag: int = 0
    position_offset: tuple = (0.0, 0.0, 0.0)
    ik: Optional[dict] = None


@dataclass
class Morph:
    name: str
    name_en: str = ""
    panel: int = 0
    type: int = 0
    offsets: list = field(default_factory=list)


@dataclass
class Material:
    name: str
    name_en: str = ""
    diffuse: tuple = (1.0, 1.0, 1.0, 1.0)
    specular: tuple = (0.0, 0.0, 0.0)
    specular_strength: float = 0.0
    ambient: tuple = (0.0, 0.0, 0.0)
    flag: int = 0
    edge_color: tuple = (0.0, 0.0, 0.0, 1.0)
    edge_size: float = 1.0
    texture_index: int = 0
    sphere_texture_index: int = -1
    sphere_mode: int = 0
    toon_flag: int = 0
    toon_texture_index: int = -1
    memo: str = ""
    face_count: int = 0


@dataclass
class ModelIR:
    ir_version: str = IR_VERSION
    format: str = "pmx"
    model_name: str = ""
    model_name_en: str = ""
    comment: str = ""
    comment_en: str = ""
    pmx_version: float = 2.0
    encoding: str = "utf-16le"
    index_sizes: dict = field(default_factory=dict)
    additional_uv: int = 0
    counts: dict = field(default_factory=dict)
    bones: list = field(default_factory=list)
    morphs: list = field(default_factory=list)
    materials: list = field(default_factory=list)
    rigid_bodies: list = field(default_factory=list)
    joints: list = field(default_factory=list)
    report: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class MotionIR:
    ir_version: str = IR_VERSION
    format: str = "vmd"
    model_name: str = ""
    bone_frames: list = field(default_factory=list)
    morph_frames: list = field(default_factory=list)
    camera_frames: list = field(default_factory=list)
    light_frames: list = field(default_factory=list)
    self_shadow_frames: list = field(default_factory=list)
    ik_frames: list = field(default_factory=list)
    report: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def require_ir_version(data: dict, expected: str = IR_VERSION) -> None:
    got = data.get("ir_version")
    if got != expected:
        raise ValueError("IR version mismatch: expected %r, got %r" % (expected, got))
