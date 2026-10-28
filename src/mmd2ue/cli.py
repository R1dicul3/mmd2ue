"""CLI entry point: inspect / convert-model / convert-motion / convert-camera.

Reference: docs/stage1-requirements.md §2.1 (D-M1-4). Writes JSON without BOM
(constraint C4). All standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from mmd2ue.core.ir import IR_VERSION
from mmd2ue.core.parsers import pmx, vmd


def _write_json(obj, path: str) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    # No BOM, UTF-8 (constraint C4).
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def cmd_inspect(args) -> int:
    path = args.path
    if not os.path.isfile(path):
        print("error: file not found: %s" % path, file=sys.stderr)
        return 2
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pmx":
        model = pmx.parse_file(path)
        info = {
            "ir_version": IR_VERSION,
            "format": "pmx",
            "model_name": model.model_name,
            "model_name_en": model.model_name_en,
            "pmx_version": model.pmx_version,
            "encoding": model.encoding,
            "counts": model.counts,
            "report": model.report,
        }
    elif ext == ".vmd":
        motion = vmd.parse_file(path)
        info = {
            "ir_version": IR_VERSION,
            "format": "vmd",
            "model_name": motion.model_name,
            "counts": {
                "bones": len(motion.bone_frames),
                "morphs": len(motion.morph_frames),
                "cameras": len(motion.camera_frames),
                "lights": len(motion.light_frames),
                "self_shadows": len(motion.self_shadow_frames),
                "ik": len(motion.ik_frames),
            },
            "report": motion.report,
        }
    else:
        print("error: unsupported file extension %r" % ext, file=sys.stderr)
        return 2
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def cmd_convert_model(args) -> int:
    model = pmx.parse_file(args.path)
    ir = model.to_dict()
    _write_json(ir, args.output)
    print("wrote %s (%d bones, %d materials, %d morphs)" % (
        args.output, model.counts.get("bones", 0),
        model.counts.get("materials", 0), model.counts.get("morphs", 0)))
    return 0


def cmd_convert_motion(args) -> int:
    motion = vmd.parse_file(args.path)
    ir = motion.to_dict()
    _write_json(ir, args.output)
    print("wrote %s (%d bone frames, %d morph frames, %d camera frames)" % (
        args.output, len(motion.bone_frames), len(motion.morph_frames),
        len(motion.camera_frames)))
    return 0


def cmd_convert_camera(args) -> int:
    motion = vmd.parse_file(args.path)
    out = {
        "ir_version": IR_VERSION,
        "format": "vmd-camera",
        "model_name": motion.model_name,
        "camera_frames": motion.camera_frames,
        "report": motion.report,
    }
    _write_json(out, args.output)
    print("wrote %s (%d camera frames)" % (args.output, len(motion.camera_frames)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mmd2ue", description="MMD -> UE5.8 converter")
    parser.add_argument("--version", action="version",
                        version="mmd2ue (IR %s)" % IR_VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inspect", help="inspect a PMX/VMD file")
    p.add_argument("path")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("convert-model", help="convert PMX -> model IR JSON")
    p.add_argument("path")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_convert_model)

    p = sub.add_parser("convert-motion", help="convert VMD -> motion IR JSON")
    p.add_argument("path")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_convert_motion)

    p = sub.add_parser("convert-camera", help="convert VMD -> camera IR JSON")
    p.add_argument("path")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_convert_camera)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:  # noqa: BLE001 - top-level CLI guard
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
