#!/usr/bin/env python3
"""Shim: run PBIP smoke from repo root (`S:\\MOPR\\IT\\sid`).

The real script lives under `legal_bi_pbip_kit/scripts/` and expects
that directory as cwd so it can find `output/` and `generate_legal_bi_pbip.py`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PKG = _REPO / "legal_bi_pbip_kit"
_SCRIPT = _PKG / "scripts" / "smoke_pbip.py"


def main() -> int:
    if not _SCRIPT.is_file():
        print("smoke_pbip shim: missing", _SCRIPT, file=sys.stderr)
        return 1
    return subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=str(_PKG),
        check=False,
    ).returncode


if __name__ == "__main__":
    sys.exit(main())
