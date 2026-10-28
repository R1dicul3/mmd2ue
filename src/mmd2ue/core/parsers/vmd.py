"""VMD motion parser (bone / morph / camera / light / self-shadow / IK).

Reference: docs/stage1-requirements.md §2.2. VMD model name and bone/morph names
are Shift-JIS. We decode as CP932 and, on decode failure, keep the raw bytes as
hex, marking the event in the report (never silently replace). Bone frames are
sorted by frame number; same-name same-frame conflicts follow the spec rule
(last occurrence wins).

Constraints C2/C3: standard library only.
"""

from __future__ import annotations

import struct
from mmd2ue.core.ir import MotionIR

VMD_SIGNATURE = b"Vocaloid Motion Data 0002"
VMD_SIGNATURE_FULL = b"Vocaloid Motion Data 0002" + b"\x00" * 5


class ParserError(ValueError):
    """Raised on malformed VMD input."""


def _decode_cp932(raw: bytes) -> str:
    """Decode a Shift-JIS / CP932 name. On failure keep raw bytes as hex."""
    try:
        return raw.decode("cp932", errors="strict")
    except UnicodeDecodeError:
        return "<hex:%s>" % raw.hex()


def _cstring(raw: bytes) -> bytes:
    """Cut at the first NUL byte (fixed-width NUL-padded field)."""
    return raw.split(b"\x00", 1)[0]


def _take(raw: bytes, off: int, n: int) -> bytes:
    if off < 0 or n < 0:
        raise ParserError("negative read")
    if off + n > len(raw):
        raise ParserError("unexpected end of data at offset %d" % off)
    return raw[off:off + n]


def parse(data: bytes) -> MotionIR:
    ir = MotionIR()
    decoded_failures = 0

    sig = data[:30]
    if sig != VMD_SIGNATURE_FULL and not sig.startswith(VMD_SIGNATURE):
        raise ParserError("not a VMD file: bad signature")
    pos = 30

    name_raw = _cstring(_take(data, pos, 20))
    pos += 20
    model_name = _decode_cp932(name_raw)
    if model_name.startswith("<hex:"):
        decoded_failures += 1
    ir.model_name = model_name

    # Bone frames.
    bone_count = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
    bone_frames = []
    for _ in range(bone_count):
        raw_name = _cstring(_take(data, pos, 15)); pos += 15
        name = _decode_cp932(raw_name)
        if name.startswith("<hex:"):
            decoded_failures += 1
        frame_no = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
        pos_vals = struct.unpack("<3f", _take(data, pos, 12)); pos += 12
        rot = struct.unpack("<4f", _take(data, pos, 16)); pos += 16
        interp = list(_take(data, pos, 64)); pos += 64
        bone_frames.append({
            "name": name, "frame": frame_no,
            "position": list(pos_vals), "rotation": list(rot),
            "interpolation": interp,
        })
    bone_frames.sort(key=lambda f: f["frame"])
    # same-name same-frame => last wins (MMD keeps the last written frame)
    dedup = {(f["name"], f["frame"]): f for f in bone_frames}
    ir.bone_frames = [dedup[k] for k in sorted(dedup, key=lambda k: (k[1], k[0]))]

    # Morph frames.
    morph_count = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
    morph_frames = []
    for _ in range(morph_count):
        raw_name = _cstring(_take(data, pos, 15)); pos += 15
        name = _decode_cp932(raw_name)
        if name.startswith("<hex:"):
            decoded_failures += 1
        frame_no = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
        weight = struct.unpack("<f", _take(data, pos, 4))[0]; pos += 4
        morph_frames.append({"name": name, "frame": frame_no, "weight": weight})
    morph_frames.sort(key=lambda f: f["frame"])
    ir.morph_frames = morph_frames

    # Camera frames.
    camera_count = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
    camera_frames = []
    for _ in range(camera_count):
        frame_no = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
        distance = struct.unpack("<f", _take(data, pos, 4))[0]; pos += 4
        pos_vals = struct.unpack("<3f", _take(data, pos, 12)); pos += 12
        rot = struct.unpack("<3f", _take(data, pos, 12)); pos += 12
        interp = list(_take(data, pos, 24)); pos += 24
        fov = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
        perspective = struct.unpack("<B", _take(data, pos, 1))[0]; pos += 1
        camera_frames.append({
            "frame": frame_no, "distance": distance,
            "position": list(pos_vals), "rotation": list(rot),
            "interpolation": interp, "fov": fov, "perspective": bool(perspective),
        })
    camera_frames.sort(key=lambda f: f["frame"])
    ir.camera_frames = camera_frames

    # Light frames.
    light_count = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
    light_frames = []
    for _ in range(light_count):
        frame_no = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
        color = struct.unpack("<3f", _take(data, pos, 12)); pos += 12
        direction = struct.unpack("<3f", _take(data, pos, 12)); pos += 12
        light_frames.append({
            "frame": frame_no, "color": list(color), "direction": list(direction),
        })
    light_frames.sort(key=lambda f: f["frame"])
    ir.light_frames = light_frames

    # Self-shadow frames.
    shadow_count = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
    shadow_frames = []
    for _ in range(shadow_count):
        frame_no = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
        mode = struct.unpack("<B", _take(data, pos, 1))[0]; pos += 1
        distance = struct.unpack("<f", _take(data, pos, 4))[0]; pos += 4
        shadow_frames.append({"frame": frame_no, "mode": mode, "distance": distance})
    shadow_frames.sort(key=lambda f: f["frame"])
    ir.self_shadow_frames = shadow_frames

    # IK on/off frames.
    ik_count = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
    ik_frames = []
    for _ in range(ik_count):
        frame_no = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
        show = struct.unpack("<B", _take(data, pos, 1))[0]; pos += 1
        n_ik = struct.unpack("<I", _take(data, pos, 4))[0]; pos += 4
        ik_names = []
        for _ in range(n_ik):
            raw_name = _cstring(_take(data, pos, 20)); pos += 20
            name = _decode_cp932(raw_name)
            if name.startswith("<hex:"):
                decoded_failures += 1
            enabled = struct.unpack("<B", _take(data, pos, 1))[0]; pos += 1
            ik_names.append({"name": name, "enabled": bool(enabled)})
        ik_frames.append({"frame": frame_no, "show": show, "ik": ik_names})
    ik_frames.sort(key=lambda f: f["frame"])
    ir.ik_frames = ik_frames

    # units semantics (see core/ir.py): for VMD, units = bone + morph + camera
    # frame count. "skipped" is 0 because this parser fully parses all six blocks
    # (bone/morph/camera/light/self-shadow/IK) and drops nothing; a CP932 decode
    # failure is an *approximation* (name kept as "<hex:...>"), not a skip, so it
    # is counted under "approximated" (decoded_failures).
    ir.report = {
        "units": bone_count + morph_count + camera_count,
        "skipped": 0,
        "approximated": decoded_failures,
    }
    return ir


def parse_file(path: str) -> MotionIR:
    with open(path, "rb") as fh:
        return parse(fh.read())
