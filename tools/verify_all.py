#!/usr/bin/env python3
"""Five-step merge gate (docs/stage1-requirements.md §1.2).

Runs, in order (any failure blocks merge):
  1. Unit tests (tests/unit)
  2. Golden comparison (tests/golden)
  3. Conversion report check: report must contain units/skipped/approximated
  4. LICENSE file existence check
  5. Asset leak check: no *.pmx / *.vmd / *.pmm / *.wav / *.mp3 / *.tga / *.bmp
     entity assets anywhere in the repo (samples/ must only hold self-generated
     synthetic inputs)

Exits 0 only when all five steps pass.
"""

from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Make the gate self-sufficient regardless of how the package is installed:
# put src/ and the local .deps/ (pytest + deps) on sys.path and PYTHONPATH so
# 'python tools/verify_all.py' works without a completed pip editable install.
_SRC = os.path.join(ROOT, "src")
_DEPS = os.path.join(ROOT, ".deps")
for _p in (_SRC, _DEPS):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
_env = os.environ.get("PYTHONPATH", "")
os.environ["PYTHONPATH"] = os.pathsep.join(
    [_p for _p in (_SRC, _DEPS, _env) if _p]
)

# Asset extensions that must never be committed (constraint C5).
FORBIDDEN_EXTS = {".pmx", ".vmd", ".pmm", ".wav", ".mp3", ".flac", ".ogg",
                   ".tga", ".bmp"}


def step(n: int, title: str) -> None:
    print("\n[%d/5] %s" % (n, title), flush=True)


def run(cmd: list[str]) -> int:
    print("  + " + " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT)


def check_report_keys() -> bool:
    """Step 3: every parser report must carry units/skipped/approximated."""
    sys.path.insert(0, os.path.join(ROOT, "src"))
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        import gen_samples
        from mmd2ue.core.parsers import pmx, vmd
        pmx_ir = pmx.parse(gen_samples.build_pmx_v2(2.0, "utf-16le"))
        vmd_ir = vmd.parse(gen_samples.build_vmd())
    except Exception as e:  # noqa: BLE001
        print("  ! failed to load parser: %s" % e)
        return False

    ok = True
    for label, report in (("pmx", pmx_ir.report), ("vmd", vmd_ir.report)):
        missing = [k for k in ("units", "skipped", "approximated") if k not in report]
        if missing:
            print("  ! %s report missing keys: %s" % (label, missing))
            ok = False
        else:
            print("  ok %s report: units=%s skipped=%s approximated=%s"
                  % (label, report["units"], report["skipped"], report["approximated"]))
    return ok


def check_license() -> bool:
    """Step 4: LICENSE file must exist at repo root."""
    license_path = os.path.join(ROOT, "LICENSE")
    if os.path.isfile(license_path) and os.path.getsize(license_path) > 0:
        print("  ok LICENSE present (%d bytes)" % os.path.getsize(license_path))
        return True
    print("  ! LICENSE missing or empty")
    return False


# Directories that are never version-controlled (mirrors .gitignore). When
# git is unavailable (fresh pre-commit tree) we prune these from the os.walk
# scan so build/cache artifacts cannot cause false-red asset-leak failures.
IGNORED_DIRS = {".git", ".deps", ".deps-install", "tmp", "build", "dist",
                ".venv", "venv", "__pycache__", "pytest-cache-files"}


def _ignored_dir(relpath: str) -> bool:
    parts = relpath.replace(os.sep, "/").split("/")
    for part in parts:
        if part in IGNORED_DIRS or part.startswith("pytest-cache-files-"):
            return True
    return False


def check_asset_leak() -> bool:
    """Step 5: no forbidden entity assets anywhere in the repo.

    Two defences (R3/R4):
    1. the walk prunes gitignored directories so cache/tool dirs cannot cause a
       false red;
    2. any forbidden-extension file found under samples/ must byte-match the
       synthetic builder output (sha256), otherwise it is treated as a real
       asset and the gate FAILs.
    """
    offenders = []
    for dirpath, _dirnames, filenames in os.walk(ROOT):
        rel = os.path.relpath(dirpath, ROOT)
        if rel == ".":
            rel = ""
        if rel and _ignored_dir(rel):
            continue
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in FORBIDDEN_EXTS:
                offenders.append(os.path.join(dirpath, fn))

    if not offenders:
        print("  ok no forbidden entity assets in repo")
        return True

    # Everything found must be a self-generated synthetic sample under samples/.
    for o in offenders:
        print("  ! forbidden-extension file: %s" % os.path.relpath(o, ROOT))

    synthetic = [o for o in offenders
                 if os.path.relpath(o, ROOT).replace(os.sep, "/").startswith("samples/")]
    if len(synthetic) != len(offenders):
        print("  ! forbidden extension outside samples/ — FAIL")
        return False

    return _samples_match_generator(synthetic)


def _samples_match_generator(paths) -> bool:
    """Every samples/*.pmx|.vmd must byte-match the gen_samples builder output."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        import gen_samples  # noqa: F401
    except Exception as e:  # noqa: BLE001
        print("  ! cannot import tools/gen_samples.py: %s" % e)
        return False
    import hashlib

    builders = {
        "pmx20_utf16le.pmx": gen_samples.build_pmx_v2(2.0, "utf-16le"),
        "pmx21_utf8.pmx": gen_samples.build_pmx_v2(2.1, "utf-8"),
        "motion.vmd": gen_samples.build_vmd(),
    }
    ok = True
    for path in sorted(paths):
        name = os.path.basename(path)
        expected = builders.get(name)
        if expected is None:
            print("  ! unexpected sample file (not generated by gen_samples): %s" % name)
            ok = False
            continue
        with open(path, "rb") as fh:
            actual = fh.read()
        if hashlib.sha256(actual).digest() != hashlib.sha256(expected).digest():
            print("  ! sample %s does not byte-match gen_samples output — FAIL" % name)
            ok = False
        else:
            print("  ok synthetic sample %s byte-matches generator" % name)
    return ok


def main() -> int:
    print("verify_all: five-step gate (root=%s)" % ROOT, flush=True)

    step(1, "unit tests")
    if run([sys.executable, "-m", "pytest", "tests/unit", "-q"]) != 0:
        print("FAIL: step 1 (unit tests)")
        return 1

    step(2, "golden comparison")
    if run([sys.executable, "-m", "pytest", "tests/golden", "-q"]) != 0:
        print("FAIL: step 2 (golden)")
        return 1

    step(3, "report keys (units/skipped/approximated)")
    if not check_report_keys():
        print("FAIL: step 3 (report keys)")
        return 1

    step(4, "license existence")
    if not check_license():
        print("FAIL: step 4 (license)")
        return 1

    step(5, "asset leak")
    if not check_asset_leak():
        print("FAIL: step 5 (asset leak)")
        return 1

    print("\nALL FIVE STEPS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
