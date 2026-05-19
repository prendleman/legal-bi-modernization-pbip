#!/usr/bin/env python3
"""Render a single self-contained HTML dashboard mockup from synthetic CSVs.

Produces previews/dashboard_mockup.html - a one-pager that aggregates real
numbers from the synthetic gold CSVs into a Power BI-styled layout. Tiles
mirror what the PBIP report shows in Desktop. The page banner makes the
intent obvious: this is a mockup, not a Power BI screenshot.

Requires: pandas (matplotlib not needed). Charts are inline SVG.

Run:
    py legal_bi_pbip_kit\\scripts\\build_html_mockup.py
"""
from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "legal_bi_pbip_kit" / "output_test" / "Sidley_BI_Modernization_Demo" / "data"
OUT = REPO / "previews" / "dashboard_mockup.html"

NAVY = "#0E2A47"
GOLD = "#B68C2E"


def _load() -> dict[str, pd.DataFrame]:
    files = [
        "fact_billings", "fact_time_entries", "fact_legacy_report_inventory",
        "fact_refresh_log", "fact_requirements_backlog",
        "dim_practice", "dim_office", "dim_client", "dim_matter",
    ]
    return {f: pd.read_csv(DATA / f"{f}.csv") for f in files}


def _as_of(rl: pd.DataFrame) -> str:
    dk = int(rl["DateKey"].max())
    s = str(dk)
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def _svg_bar_chart(values: list[tuple[str, float]], unit: str = "$M", color: str = NAVY,
                   width: int = 360, height: int = 200, max_label_chars: int = 16) -> str:
    if not values:
        return ""
    max_v = max(v for _, v in values) or 1
    label_w = 110
    bar_h = (height - 16) / len(values)
    bars = []
    for i, (label, v) in enumerate(values):
        y = 8 + i * bar_h
        w = (v / max_v) * (width - label_w - 60)
        short = (label[:max_label_chars] + "...") if len(label) > max_label_chars else label
        bars.append(
            f'<text x="{label_w - 6}" y="{y + bar_h / 2 + 4}" text-anchor="end" '
            f'font-size="11" fill="#1a1a1a">{html.escape(short)}</text>'
            f'<rect x="{label_w}" y="{y + bar_h * 0.15}" width="{w:.1f}" '
            f'height="{bar_h * 0.7:.1f}" fill="{color}" />'
            f'<text x="{label_w + w + 4}" y="{y + bar_h / 2 + 4}" font-size="11" '
            f'fill="#1a1a1a">{html.escape(_fmt(v, unit))}</text>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" preserveAspectRatio="xMidYMid meet" '
        f'role="img">{"".join(bars)}</svg>'
    )


def _svg_line_chart(points: list[tuple[str, float]], unit: str = "$M",
                    color: str = NAVY, width: int = 720, height: int = 200) -> str:
    if not points:
        return ""
    max_v = max(v for _, v in points) or 1
    min_v = min(v for _, v in points)
    pad_l, pad_r, pad_t, pad_b = 50, 16, 14, 28
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    n = len(points)
    coords = []
    for i, (_, v) in enumerate(points):
        x = pad_l + (i / max(n - 1, 1)) * plot_w
        y = pad_t + plot_h - ((v - min_v) / max(max_v - min_v, 1e-9)) * plot_h
        coords.append((x, y))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    grid = []
    for frac, lbl in [(0, max_v), (0.5, (max_v + min_v) / 2), (1.0, min_v)]:
        gy = pad_t + frac * plot_h
        grid.append(
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{pad_l + plot_w}" y2="{gy:.1f}" '
            f'stroke="#d8d8d2" stroke-width="0.6" />'
            f'<text x="{pad_l - 6}" y="{gy + 4:.1f}" text-anchor="end" font-size="10" '
            f'fill="#5a5a55">{html.escape(_fmt(lbl, unit))}</text>'
        )
    n_labels = min(6, len(points))
    step = max(len(points) // n_labels, 1)
    x_labels = []
    for i in range(0, len(points), step):
        x_labels.append(
            f'<text x="{coords[i][0]:.1f}" y="{height - 8}" text-anchor="middle" '
            f'font-size="10" fill="#5a5a55">{html.escape(points[i][0])}</text>'
        )
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{GOLD}" '
        f'stroke="{color}" stroke-width="0.8" />' for x, y in coords
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" preserveAspectRatio="xMidYMid meet" '
        f'role="img">{"".join(grid)}{"".join(x_labels)}'
        f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="1.8" />'
        f'{dots}</svg>'
    )


def _svg_donut(values: list[tuple[str, float]], palette: list[str], size: int = 220) -> str:
    total = sum(v for _, v in values) or 1
    cx, cy, r_outer, r_inner = size / 2, size / 2, size * 0.4, size * 0.24
    import math
    start = -math.pi / 2
    arcs = []
    for i, (_, v) in enumerate(values):
        frac = v / total
        end = start + frac * 2 * math.pi
        large = 1 if frac > 0.5 else 0
        x1 = cx + r_outer * math.cos(start)
        y1 = cy + r_outer * math.sin(start)
        x2 = cx + r_outer * math.cos(end)
        y2 = cy + r_outer * math.sin(end)
        x3 = cx + r_inner * math.cos(end)
        y3 = cy + r_inner * math.sin(end)
        x4 = cx + r_inner * math.cos(start)
        y4 = cy + r_inner * math.sin(start)
        path = (
            f"M{x1:.1f},{y1:.1f} A{r_outer},{r_outer} 0 {large} 1 {x2:.1f},{y2:.1f} "
            f"L{x3:.1f},{y3:.1f} A{r_inner},{r_inner} 0 {large} 0 {x4:.1f},{y4:.1f} Z"
        )
        arcs.append(
            f'<path d="{path}" fill="{palette[i % len(palette)]}" stroke="white" stroke-width="1.5" />'
        )
        start = end
    legend = "".join(
        f'<div class="legend-row"><span class="swatch" style="background:{palette[i % len(palette)]}">'
        f'</span>{html.escape(label)} <span class="muted">({_fmt(val, "n")})</span></div>'
        for i, (label, val) in enumerate(values)
    )
    return (
        f'<div class="donut-wrap">'
        f'<svg viewBox="0 0 {size} {size}" width="180" height="180" role="img">{"".join(arcs)}</svg>'
        f'<div class="legend">{legend}</div></div>'
    )


def _fmt(v: float, unit: str) -> str:
    if unit == "$M":
        return f"${v:,.1f}M"
    if unit == "$":
        return f"${v:,.0f}"
    if unit == "%":
        return f"{v:.1%}"
    if unit == "min":
        return f"{v:,.1f} min"
    if unit == "n":
        return f"{int(v):,}"
    return f"{v:,.1f}"


def _compute(d: dict[str, pd.DataFrame]) -> dict:
    bill = d["fact_billings"].merge(d["dim_practice"], on="PracticeKey").merge(d["dim_client"], on="ClientKey")
    bill["MonthYear"] = pd.to_datetime(bill["DateKey"].astype(str), format="%Y%m%d").dt.to_period("M")
    monthly = bill.groupby("MonthYear")["BillingAmount"].sum().sort_index()
    monthly_pts = [(str(p), v / 1e6) for p, v in monthly.items()]

    matters = d["dim_matter"]
    legacy = d["fact_legacy_report_inventory"]
    refresh = d["fact_refresh_log"]
    te = d["fact_time_entries"]
    bk = d["fact_requirements_backlog"]

    return {
        "as_of": _as_of(refresh),
        "kpis": {
            "billings": bill["BillingAmount"].sum(),
            "margin_pct": (bill["FeeAmount"].sum() - bill["CostAmount"].sum()) / bill["FeeAmount"].sum(),
            "billable_pct": te.loc[te["WorkType"] == "Billable", "Hours"].sum() / te["Hours"].sum(),
            "collection_rate": bill["CashCollected"].sum() / bill["BillingAmount"].sum(),
            "active_matters": int((matters["MatterStatus"] != "Closed").sum()),
            "refresh_rate": (refresh["RefreshStatus"] == "Success").mean(),
            "mig_pct": (legacy["MigrationStatus"] == "Migrated").mean(),
            "val_pct": (legacy["ValidationStatus"] == "Validated").mean(),
            "open_requests": int(bk["RequestStatus"].isin(["New", "In Discovery", "In Build", "Blocked"]).sum()),
            "sla_breach": int(bk["SLABreachFlag"].sum()),
            "legacy_count": len(legacy),
            "health_score": (legacy["MigrationStatus"].eq("Migrated").mean() * 40
                             + legacy["ValidationStatus"].eq("Validated").mean() * 30
                             + (refresh["RefreshStatus"] == "Success").mean() * 30),
        },
        "monthly": monthly_pts,
        "industry": [(name, v / 1e6) for name, v in bill.groupby("Industry")["BillingAmount"].sum()
                     .sort_values(ascending=False).items()],
        "practice_margin": [(name, ((g["FeeAmount"].sum() - g["CostAmount"].sum()) / g["FeeAmount"].sum()) * 100)
                            for name, g in bill.groupby("PracticeName")],
        "migration_mix": [(name, int(v)) for name, v in legacy["MigrationStatus"].value_counts().items()],
        "stakeholder_mix": [(name, int(v)) for name, v in bk["StakeholderGroup"].value_counts().items()],
        "office_billings": [(name, v / 1e6) for name, v in
                            bill.merge(d["dim_office"], on="OfficeKey")
                            .groupby("OfficeName")["BillingAmount"].sum()
                            .sort_values(ascending=False).items()],
    }


PALETTE = [NAVY, GOLD, "#5A5A55", "#3F5A78", "#A47A2E", "#9C9C90", "#D7C28C", "#7A7A6E"]


def _kpi_html(label: str, value: str, sub: str = "", tone: str = "navy") -> str:
    return (
        f'<div class="kpi kpi--{tone}">'
        f'<div class="kpi__label">{html.escape(label.upper())}</div>'
        f'<div class="kpi__value">{html.escape(value)}</div>'
        f'<div class="kpi__sub">{html.escape(sub)}</div></div>'
    )


def render(data: dict) -> str:
    k = data["kpis"]
    practice_sorted = sorted(data["practice_margin"], key=lambda x: x[1], reverse=True)
    kpi_row = "".join([
        _kpi_html("Total Billings", _fmt(k["billings"] / 1e6, "$M"), "Across calendar window"),
        _kpi_html("Gross Margin %", _fmt(k["margin_pct"], "%"), "Fees less direct costs", "gold"),
        _kpi_html("Billable %", _fmt(k["billable_pct"], "%"), "Billable / total hours"),
        _kpi_html("Collection Rate", _fmt(k["collection_rate"], "%"), "Cash / Billings", "gold"),
        _kpi_html("Active Matters", _fmt(k["active_matters"], "n"), "Open + On Hold"),
        _kpi_html("Refresh Success", _fmt(k["refresh_rate"], "%"), "Certified dataset health", "gold"),
    ])
    mig_row = "".join([
        _kpi_html("Legacy Reports", _fmt(k["legacy_count"], "n"), "In modernization backlog"),
        _kpi_html("Migration %", _fmt(k["mig_pct"], "%"), "Reports retired", "gold"),
        _kpi_html("Validation %", _fmt(k["val_pct"], "%"), "Parallel sign-off"),
        _kpi_html("Health Score", f'{k["health_score"]:.1f}', "0.4 / 0.3 / 0.3 blend", "gold"),
        _kpi_html("Open Requests", _fmt(k["open_requests"], "n"), "Stakeholder backlog"),
        _kpi_html("SLA Breaches", _fmt(k["sla_breach"], "n"), "Past target date", "gold"),
    ])

    body = f"""
    <header>
      <div class="banner" role="note">
        SYNTHETIC DATA MOCKUP - not a Power BI screenshot. Numbers below are aggregated from
        <code>legal_bi_pbip_kit/output_test/.../data/*.csv</code> at build time.
      </div>
      <div class="title-row">
        <div>
          <h1>Legal BI Modernization - Executive Mockup</h1>
          <div class="subtitle">Power BI on Databricks - synthetic data preview - layout style only</div>
        </div>
        <div class="as-of">As of <strong>{data['as_of']}</strong></div>
      </div>
    </header>

    <section class="kpi-grid">{kpi_row}</section>

    <section class="row">
      <div class="card card--wide">
        <div class="card__title">Billings by month ($M)</div>
        {_svg_line_chart(data['monthly'], unit='$M', width=720, height=200)}
      </div>
      <div class="card">
        <div class="card__title">Billings by industry ($M)</div>
        {_svg_bar_chart(data['industry'][:8], unit='$M', color=NAVY)}
      </div>
    </section>

    <section class="row">
      <div class="card">
        <div class="card__title">Gross margin % by practice</div>
        {_svg_bar_chart([(n, v) for n, v in practice_sorted], unit='%', color=GOLD)}
      </div>
      <div class="card">
        <div class="card__title">Billings by office ($M)</div>
        {_svg_bar_chart(data['office_billings'][:10], unit='$M', color=NAVY)}
      </div>
      <div class="card">
        <div class="card__title">Migration status mix</div>
        {_svg_donut(data['migration_mix'], PALETTE)}
      </div>
    </section>

    <h2 class="section-h">Modernization & stakeholder muscle</h2>
    <section class="kpi-grid">{mig_row}</section>

    <section class="row">
      <div class="card card--wide">
        <div class="card__title">Stakeholder request volume by group</div>
        {_svg_bar_chart(data['stakeholder_mix'], unit='n', color=NAVY)}
      </div>
      <div class="card">
        <div class="card__title">Why this is here</div>
        <div class="copy">
          <p>This page is a <strong>visual reference</strong> for what the PBIP report renders in Desktop.
          Numbers, ratios, and category counts come from the same synthetic gold CSVs the report binds to.</p>
          <p>For the actual Power BI build, open
          <code>output_test/Sidley_BI_Modernization_Demo/Sidley_BI_Modernization_Demo.pbip</code>
          in Power BI Desktop. Visual fidelity (slicers, sync groups, bookmarks, RLS, calc groups)
          lives there - this HTML cannot reproduce it.</p>
          <p class="muted">See <code>previews/pages/</code> for per-page renderings from real CSVs.</p>
        </div>
      </div>
    </section>

    <footer>
      Generated by <code>legal_bi_pbip_kit/scripts/build_html_mockup.py</code>.
      All entity names, attorneys, clients, and matters are <strong>synthetic</strong>. Not Sidley
      Austin LLP data. See <code>LICENSE</code> for the disclaimer.
    </footer>
    """

    css = """
    :root { --navy: #0E2A47; --gold: #B68C2E; --bg: #F4F4F0; --line: #C8C8C0; --text: #1A1A1A; --muted: #5A5A55; }
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; margin: 0; background: var(--bg); color: var(--text); }
    main { max-width: 1280px; margin: 0 auto; padding: 24px 28px 60px; }
    .banner { background: var(--gold); color: #1a1a1a; padding: 10px 14px; border-radius: 4px; font-size: 12.5px; font-weight: 600; margin-bottom: 18px; border-left: 4px solid var(--navy); }
    .banner code { background: rgba(14,42,71,0.08); padding: 1px 5px; border-radius: 3px; font-size: 11.5px; }
    .title-row { display: flex; justify-content: space-between; align-items: end; margin-bottom: 14px; }
    h1 { color: var(--navy); margin: 0 0 4px; font-size: 26px; font-weight: 700; }
    .subtitle { color: var(--muted); font-size: 13px; }
    .as-of { color: var(--navy); font-size: 13px; }
    h2.section-h { color: var(--navy); margin-top: 26px; font-size: 15px; text-transform: uppercase; letter-spacing: 0.4px; }
    .kpi-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin: 14px 0 20px; }
    .kpi { background: white; border: 1px solid var(--line); border-radius: 4px; padding: 12px 14px; }
    .kpi--navy { border-left: 4px solid var(--navy); }
    .kpi--gold { border-left: 4px solid var(--gold); }
    .kpi__label { font-size: 10.5px; font-weight: 700; color: var(--muted); letter-spacing: 0.5px; }
    .kpi__value { font-size: 24px; font-weight: 700; color: var(--navy); margin: 4px 0 2px; }
    .kpi__sub { font-size: 11px; color: var(--muted); }
    .row { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 14px; margin-bottom: 14px; }
    .card { background: white; border: 1px solid var(--line); border-radius: 4px; padding: 14px 14px 18px; min-height: 240px; }
    .card--wide { grid-column: span 2; }
    .card__title { font-size: 13px; font-weight: 700; color: var(--navy); margin-bottom: 10px; }
    .donut-wrap { display: flex; gap: 16px; align-items: center; }
    .legend { font-size: 11.5px; color: var(--text); }
    .legend-row { display: flex; align-items: center; gap: 6px; margin: 2px 0; }
    .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; }
    .muted { color: var(--muted); }
    .copy p { font-size: 12.5px; line-height: 1.45; margin: 0 0 8px; }
    code { font-family: 'Cascadia Code', 'SFMono-Regular', Consolas, monospace; font-size: 11.5px; background: rgba(14,42,71,0.06); padding: 1px 5px; border-radius: 3px; }
    footer { margin-top: 30px; padding-top: 16px; border-top: 1px solid var(--line); font-size: 11.5px; color: var(--muted); }
    @media (max-width: 980px) {
      .kpi-grid { grid-template-columns: repeat(3, 1fr); }
      .row { grid-template-columns: 1fr; }
      .card--wide { grid-column: span 1; }
    }
    """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Legal BI Modernization - Synthetic Mockup</title>
  <style>{css}</style>
</head>
<body><main>{body}</main></body>
</html>
"""


def main() -> int:
    if not DATA.is_dir():
        print(f"missing data dir {DATA}; run generate_legal_bi_pbip.py first", flush=True)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d = _load()
    data = _compute(d)
    OUT.write_text(render(data), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO).as_posix()} ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
