#!/usr/bin/env python3
"""CI smoke: run the PBIP generator and parse every JSON file under the output report.

Exit codes: 0 = OK, 1 = JSON/schema failure or missing paths, 2 = generator failed.
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import time
from pathlib import Path


def _page_order_len_from_generator(gen_path: Path) -> int:
    """How many report tabs `generate_legal_bi_pbip` should emit (length of PAGE_NAMES)."""
    tree = ast.parse(gen_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "PAGE_NAMES":
                if isinstance(node.value, ast.List):
                    return len(node.value.elts)
    raise ValueError(f"smoke_pbip: no PAGE_NAMES = [ ... ] assignment in {gen_path}")


def _fact_billings_m_nav_guard(model_bim: Path) -> str | None:
    """Ensure PQ M uses NavItem/Text.Combine (avoids self-ref cycle with query name)."""
    if not model_bim.is_file():
        return f"missing semantic model {model_bim}"
    try:
        root = json.loads(model_bim.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return f"model.bim JSON: {exc}"
    tables = root.get("model", {}).get("tables")
    if not isinstance(tables, list):
        return "model.bim: model.tables not found"
    expr = None
    for t in tables:
        if isinstance(t, dict) and t.get("name") == "fact_billings":
            parts = t.get("partitions") or []
            if parts and isinstance(parts[0], dict):
                src = parts[0].get("source") or {}
                expr = src.get("expression")
            break
    if not expr or not isinstance(expr, str):
        return "fact_billings partition M expression not found"
    if "NavItem" not in expr or "Text.Combine" not in expr or "[Item = NavItem" not in expr:
        return "fact_billings M missing NavItem / Text.Combine / [Item = NavItem] guard pattern"
    return None


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
GEN = PACKAGE_ROOT / "scripts" / "generate_legal_bi_pbip.py"
PROJECT = "Sidley_BI_Modernization_Demo"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Sidley PBIP and smoke-test JSON + page count.")
    parser.add_argument(
        "--skip-gen",
        action="store_true",
        help="Do not run generate_legal_bi_pbip.py; only validate existing output/ (faster local check).",
    )
    parser.add_argument(
        "--interview",
        action="store_true",
        help="Forward --interview to the generator (smaller fact_time_entries for a lighter PBIX).",
    )
    args = parser.parse_args(argv)

    if not GEN.is_file():
        print("smoke_pbip: missing generator — run from repo root:", file=sys.stderr)
        print("  cd legal_bi_pbip_kit", file=sys.stderr)
        print("  py scripts\\smoke_pbip.py", file=sys.stderr)
        print(f"  (expected {GEN})", file=sys.stderr)
        return 2
    print(f"smoke_pbip: package_root={PACKAGE_ROOT}")
    t0 = time.perf_counter()
    if not args.skip_gen:
        gen_cmd = [sys.executable, str(GEN)]
        if args.interview:
            gen_cmd.append("--interview")
        r = subprocess.run(gen_cmd, cwd=str(PACKAGE_ROOT), check=False)
        if r.returncode != 0:
            print("smoke_pbip: generator exit", r.returncode, file=sys.stderr)
            return 2
        print(f"smoke_pbip: generator elapsed {time.perf_counter() - t0:.1f}s")
    else:
        print("smoke_pbip: skipped generator (--skip-gen)")

    out = PACKAGE_ROOT / "output" / PROJECT
    report = out / f"{PROJECT}.Report" / "definition"
    model_bim = out / f"{PROJECT}.SemanticModel" / "model.bim"
    if not report.is_dir():
        print("smoke_pbip: missing", report, file=sys.stderr)
        return 1

    nav_err = _fact_billings_m_nav_guard(model_bim)
    if nav_err:
        print(f"smoke_pbip: model check failed: {nav_err}", file=sys.stderr)
        return 1

    failures: list[tuple[str, str]] = []
    n = 0
    t_json = time.perf_counter()
    for p in sorted(out.rglob("*.json")):
        n += 1
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            failures.append((str(p.relative_to(out)), str(exc)))

    pages_json = report / "pages" / "pages.json"
    po = json.loads(pages_json.read_text(encoding="utf-8"))
    page_count = len(po.get("pageOrder", []))
    expected_pages = _page_order_len_from_generator(GEN)

    print(f"smoke_pbip: parsed {n} JSON files under output/{PROJECT} in {time.perf_counter() - t_json:.1f}s")
    print(f"smoke_pbip: pages.json pageOrder count = {page_count} (expected {expected_pages} from PAGE_NAMES)")
    if failures:
        print("smoke_pbip: JSON failures:", file=sys.stderr)
        for path, msg in failures[:20]:
            print(f"  {path}: {msg}", file=sys.stderr)
        return 1
    if page_count != expected_pages:
        print(
            f"smoke_pbip: pageOrder length {page_count} != PAGE_NAMES length {expected_pages}",
            file=sys.stderr,
        )
        return 1
    print(f"smoke_pbip: OK (total {time.perf_counter() - t0:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
