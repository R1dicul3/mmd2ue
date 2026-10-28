"""VPD pose parser (optional per D-M1-7).

VPD is a text pose format used by MMD. This is a minimal, optional parser:
it reads the plain-text structure into a small dict. Kept deliberately minimal;
the primary required parsers are PMX (D-M1-1) and VMD (D-M1-2).
"""

from __future__ import annotations

from typing import Any


def parse(text: str) -> dict[str, Any]:
    """Parse VPD text into {'model_name': str, 'bones': {...}}.

    Minimal implementation: no heavy validation, standard library only.
    """
    lines = text.splitlines()
    model_name = ""
    bones: dict[str, dict[str, float]] = {}
    section = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.endswith("{") and line[:-1].strip():  # "bone_name{"
            section = line[:-1].strip()
            bones[section] = {}
        elif line == "}":
            section = None
        elif section is not None and ";" in line:
            key, _, val = line.partition(";")
            key = key.strip()
            val = val.split(";")[0].strip()
            try:
                bones[section][key] = float(val)
            except ValueError:
                bones[section][key] = val
        elif "; " in line or (section is None and ";" in line):
            # top-level magic / model name not strictly parsed here
            pass
    return {"model_name": model_name, "bones": bones}


def parse_file(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="shift_jis", errors="replace") as fh:
        return parse(fh.read())
