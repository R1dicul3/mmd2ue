"""Intermediate Representation (IR) data structures.

The IR is the single source of truth shared between the core parsers and the
future UE adaptation layer (adapters/ue5_8/). Every produced artifact carries
an ir_version; loading refuses a mismatched version (no implicit compatibility).

Report ``units`` semantics (per report producer; the three reports intentionally
use different units — aggregate within one producer only, or convert using the
definition below, see docs/stage2-requirements.md §8):
  - PMX parse:        ``units = 1`` — one model per file (vertex/material/bone
    counts are under ``ir.counts``, not under ``units``).
  - VMD parse:        ``units = bone + morph + camera frame count`` — motion
    segments parsed.
  - glTF export:      ``units = vertex count`` — vertices written to the mesh.

Bone ``position`` semantics: PMX 2.0 defines bone.position as the LOCAL
(parent-relative) translation (felixjones spec: "Position | vec3 | The local
translation of the bone"), so the parser passes it through unchanged; the
absolute (model-space) rest transform is the parent-chain accumulation
(parent_absolute + position). Vertex ``position`` is model-space absolute.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

IR_VERSION = "0.1.0"


@dataclass
class Vertex:
    """A single mesh vertex with skinned joints/weights (BDEF1/2/4; SDEF->BDEF2).

    ``joints`` / ``weights`` are parallel lists of up to 4 bone indices and
    their float weights. BDEF1 has one entry (joint 0, weight 1.0). SDEF
    (weight type 3) is approximated as BDEF2 from its first two bones +
    weight, matching the parser's existing approximation policy.
    """
    position: tuple = (0.0, 0.0, 0.0)
    normal: tuple = (0.0, 0.0, 1.0)
    uv: tuple = (0.0, 0.0)
    joints: list = field(default_factory=list)
    weights: list = field(default_factory=list)
    weight_type: int = 0
    edge_scale: float = 1.0


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
    vertices: list = field(default_factory=list)
    faces: list = field(default_factory=list)
    textures: list = field(default_factory=list)
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
