#!/usr/bin/env python3
"""Eight-step merge gate (stage 1 §1.2 + stage 2 §4 glTF/asset extensions).

Runs, in order (any failure blocks merge):
  1. Unit tests (tests/unit)
  2. Golden comparison (tests/golden)
  3. Conversion report check: report must contain units/skipped/approximated
  4. LICENSE file existence check
  5. Asset leak check: no forbidden entity assets in the repo
  6. glTF export golden comparison (stage 2, D-M2-4 / AC-M2-4)
  7. glTF export report check (stage 2, D-M2-5 / AC-M2-8)
  8. Distribution tree check (git ls-files / sdist SOURCES.txt, ADR-006)
     (5 continued) no *.pmx / *.vmd / *.pmm / *.wav / *.mp3 / *.tga / *.bmp
     entity assets anywhere in the repo (samples/ must only hold self-generated
     synthetic inputs)

Exits 0 only when all eight steps pass.
"""

from __future__ import annotations

import json
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

# Asset extensions that must never be committed (constraint C5 + ADR-006).
# Model/motion/audio AND borrowed-image extensions (F5).
FORBIDDEN_EXTS = {
    ".pmx", ".vmd", ".vpd", ".pmm",                       # model / motion
    ".wav", ".mp3", ".flac", ".ogg", ".aac",              # audio
    ".tga", ".bmp", ".png", ".jpg", ".jpeg", ".dds",      # images
    ".tif", ".tiff", ".psd", ".gif", ".webp", ".hdr", ".exr",
}


def step(n: int, title: str) -> None:
    print("\n[%d/8] %s" % (n, title), flush=True)


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


def check_gltf_golden() -> bool:
    """Step 6: core glTF exporter output matches the hand-authored golden.

    Uses the synthetic PMX sample (build_pmx_gltf) and compares the exporter
    output against tests/golden/gltf/golden_gltf.json with float rounding to
    3 decimals (numeric tolerance per docs/stage2-requirements.md §4).
    """
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        import gen_samples
        from mmd2ue.core.parsers import pmx
        from mmd2ue.core.export import gltf
    except Exception as e:  # noqa: BLE001
        print("  ! failed to load exporter: %s" % e)
        return False

    ir = pmx.parse(gen_samples.build_pmx_gltf())
    g, bin_data, _report = gltf.export_gltf(ir)

    golden_path = os.path.join(ROOT, "tests", "golden", "gltf", "golden_gltf.json")
    if not os.path.isfile(golden_path):
        print("  ! golden glTF missing: %s" % golden_path)
        return False
    with open(golden_path, encoding="utf-8") as fh:
        golden = json.load(fh)

    if _round3(g) != _round3(golden):
        print("  ! glTF golden mismatch — FAIL")
        return False
    if g["buffers"][0]["byteLength"] != len(bin_data):
        print("  ! glTF buffer byteLength != .bin size — FAIL")
        return False
    print("  ok glTF golden matches (buffer=%d bytes)" % len(bin_data))
    return True


def check_gltf_report() -> bool:
    """Step 7: glTF export report lists ignored items + canonical keys.

    AC-M2-8: the report must list, per material, the ignored/approximated
    material features (sphere map / toon / edge) as required by
    docs/stage2-requirements.md §3; and must carry the canonical
    units/skipped/approximated keys (parser convention, F3).
    """
    try:
        import gen_samples
        from mmd2ue.core.parsers import pmx
        from mmd2ue.core.export import gltf
    except Exception as e:  # noqa: BLE001
        print("  ! failed to load exporter: %s" % e)
        return False

    ir = pmx.parse(gen_samples.build_pmx_gltf())
    _g, _bin_data, report = gltf.export_gltf(ir)
    d = report.to_dict()

    ok = True
    # Canonical keys (F3).
    missing_keys = [k for k in ("units", "skipped", "approximated") if k not in d]
    if missing_keys:
        print("  ! glTF report missing keys: %s — FAIL" % (missing_keys,))
        ok = False
    else:
        print("  ok glTF report keys: units=%s skipped=%s approximated=%s"
              % (d["units"], d["skipped"], d["approximated"]))

    # Ignored material items (sphere_map/toon/edge).
    ignored = d.get("ignored_materials", [])
    if not ignored:
        print("  ! report lists no ignored materials — FAIL")
        return False
    items = ignored[0]["items"]
    missing_items = [k for k in ("sphere_map", "toon", "edge") if k not in items]
    if missing_items:
        print("  ! glTF report missing ignored items: %s — FAIL" % (missing_items,))
        ok = False
    else:
        print("  ok glTF report lists ignored items: %s" % (", ".join(items)))

    # External texture references (F7).
    refs = d.get("texture_refs", [])
    if not refs:
        print("  ! glTF report lists no texture_refs — FAIL")
        ok = False
    else:
        print("  ok glTF report lists texture_refs: %d reference(s)" % len(refs))

    return ok


def _round3(x):
    if isinstance(x, float):
        return round(x, 3)
    if isinstance(x, list):
        return [_round3(v) for v in x]
    if isinstance(x, dict):
        return {k: _round3(v) for k, v in x.items()}
    return x



def check_distribution_tree() -> bool:
    """Step 8: distribution tree carries no entity assets (ADR-006, F5).

    Uses git ls-files (tracked files) when available, else falls back to the
    sdist SOURCES.txt manifest. Either way it asserts the shipped tree has no
    forbidden-extension asset, so "仓库与产物 tree 无实体资产" holds even
    against a gitignored local cache directory.
    """
    tracked = _git_ls_files()
    if tracked is not None:
        offenders = [f for f in tracked
                     if os.path.splitext(f)[1].lower() in FORBIDDEN_EXTS]
        if offenders:
            for o in offenders:
                print("  ! tracked asset file: %s" % o)
            print("  ! distribution tree has forbidden assets — FAIL")
            return False
        print("  ok git ls-files: %d tracked files, 0 forbidden assets" % len(tracked))
        return True

    # Fallback: sdist SOURCES.txt manifest.
    sources = os.path.join(ROOT, "src", "mmd2ue.egg-info", "SOURCES.txt")
    if not os.path.isfile(sources):
        print("  ! no git and no SOURCES.txt — cannot verify distribution tree")
        return False
    offenders = []
    with open(sources, encoding="utf-8") as fh:
        for line in fh:
            name = line.strip()
            if name and os.path.splitext(name)[1].lower() in FORBIDDEN_EXTS:
                offenders.append(name)
    if offenders:
        for o in offenders:
            print("  ! SOURCES.txt asset file: %s" % o)
        print("  ! distribution tree has forbidden assets — FAIL")
        return False
    print("  ok SOURCES.txt: 0 forbidden assets")
    return True


def _git_ls_files():
    """Return the list of git-tracked file paths, or None when git is absent."""
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        )
    except Exception:  # noqa: BLE001 - git may be unavailable
        return None
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]



def main() -> int:
    print("verify_all: eight-step gate (root=%s)" % ROOT, flush=True)

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

    step(6, "glTF export golden comparison")
    if not check_gltf_golden():
        print("FAIL: step 6 (glTF golden)")
        return 1

    step(7, "glTF export report check")
    if not check_gltf_report():
        print("FAIL: step 7 (glTF report)")
        return 1

    step(8, "distribution tree asset check")
    if not check_distribution_tree():
        print("FAIL: step 8 (distribution tree)")
        return 1

    print("\nALL EIGHT STEPS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
