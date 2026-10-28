"""Shared test fixtures: add src/tools to path and generate synthetic samples.

Synthetic samples are built in-memory from tools/gen_samples.py so the tests
never depend on committed binary .pmx/.vmd files (constraint C5).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
TOOLS = os.path.join(ROOT, "tools")
for _p in (SRC, TOOLS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import gen_samples as _gs  # noqa: E402


def sample_bytes(name: str) -> bytes:
    if name == "pmx20_utf16le.pmx":
        return _gs.build_pmx_v2(2.0, "utf-16le")
    if name == "pmx21_utf8.pmx":
        return _gs.build_pmx_v2(2.1, "utf-8")
    if name == "motion.vmd":
        return _gs.build_vmd()
    if name == "pmx_sdef.pmx":
        return _gs.build_pmx_sdef()
    if name == "pmx_qdef.pmx":
        return _gs.build_pmx_qdef()
    if name == "vmd_undecodable.vmd":
        return _gs.build_vmd_undecodable()
    if name == "vmd_ik.vmd":
        return _gs.build_vmd_ik()
    raise KeyError(name)
