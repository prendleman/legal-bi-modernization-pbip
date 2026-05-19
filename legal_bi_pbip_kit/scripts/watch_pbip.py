"""Watch generator sources and re-run generate_legal_bi_pbip.py when files change.

Stdlib only. From package root::

    py scripts/watch_pbip.py
    py scripts/watch_pbip.py --out path\\to\\output

Ctrl+C to stop.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PACKAGE_ROOT / "scripts"
POLL_INTERVAL = 0.6
DEBOUNCE_SEC = 1.2


def _watched_files() -> list[Path]:
    paths: list[Path] = []
    for p in sorted(SCRIPTS.glob("*.py")):
        if p.name == "watch_pbip.py":
            continue
        paths.append(p)
    assets = SCRIPTS / "report_assets"
    if assets.is_dir():
        paths.extend(sorted(assets.glob("*.json")))
    return paths


def _fingerprint() -> tuple[tuple[str, int], ...]:
    rows: list[tuple[str, int]] = []
    for p in _watched_files():
        try:
            st = p.stat()
            rows.append((str(p.resolve()), int(st.st_mtime_ns)))
        except OSError:
            continue
    return tuple(rows)


def _run_generate(forward_argv: list[str]) -> int:
    cmd = [sys.executable, str(SCRIPTS / "generate_legal_bi_pbip.py"), *forward_argv]
    print(f"\n--- Regenerating: {' '.join(cmd)} ---\n", flush=True)
    r = subprocess.run(cmd, cwd=str(PACKAGE_ROOT))
    return int(r.returncode)


def main() -> int:
    forward = list(sys.argv[1:])
    print(
        "Watching",
        SCRIPTS,
        "(Python + report_assets). Debounce",
        DEBOUNCE_SEC,
        "s. Ctrl+C to stop.\n",
        flush=True,
    )
    last = _fingerprint()
    _run_generate(forward)
    last = _fingerprint()
    try:
        while True:
            time.sleep(POLL_INTERVAL)
            cur = _fingerprint()
            if cur == last:
                continue
            time.sleep(DEBOUNCE_SEC)
            cur = _fingerprint()
            if cur == last:
                continue
            code = _run_generate(forward)
            last = _fingerprint()
            if code != 0:
                print(f"generate_legal_bi_pbip exited with {code} (watching continues)\n", flush=True)
    except KeyboardInterrupt:
        print("\nStopped watch.", flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(main())
