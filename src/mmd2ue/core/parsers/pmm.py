"""PMM entry placeholder.

PMM is the MikuMikuMoving project format (v2). Per docs/stage1-requirements.md
§2.1 (D-M1-7) and §2.3 (AC-M1-8): the entry point raises NotImplementedError
and must not produce corrupt data.
"""

from __future__ import annotations


def parse(data: bytes):  # pragma: no cover - placeholder
    raise NotImplementedError("PMM (MikuMikuMoving project, v2) is not supported")


def parse_file(path: str):  # pragma: no cover - placeholder
    raise NotImplementedError("PMM (MikuMikuMoving project, v2) is not supported")
