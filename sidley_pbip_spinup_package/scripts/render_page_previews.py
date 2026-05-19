#!/usr/bin/env python3
"""Render one PNG per PBIP page from the synthetic gold CSVs.

Outputs land under previews/pages/ at the repo root. Each PNG is labeled as
a SYNTHETIC DATA PREVIEW (not a Power BI screenshot) so reviewers cannot
confuse them with the real report.

Requires: matplotlib + pandas (see sidley_pbip_spinup_package/requirements-preview.txt).

Run:
    py sidley_pbip_spinup_package\\scripts\\render_page_previews.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "sidley_pbip_spinup_package" / "output_test" / "Sidley_BI_Modernization_Demo" / "data"
OUT = REPO / "previews" / "pages"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#0E2A47"
GOLD = "#B68C2E"
GREY_BG = "#F4F4F0"
GREY_LINE = "#C8C8C0"
TEXT = "#1A1A1A"
MUTED = "#5A5A55"

DISCLAIMER = "Synthetic data preview - not a Power BI screenshot"


def _style() -> None:
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": GREY_BG,
        "axes.edgecolor": GREY_LINE,
        "axes.labelcolor": TEXT,
        "xtick.color": TEXT,
        "ytick.color": TEXT,
        "axes.titleweight": "bold",
        "axes.titlecolor": NAVY,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.family": "DejaVu Sans",
        "font.size": 9,
    })


def _chrome(fig, title: str, subtitle: str, as_of: str) -> None:
    fig.suptitle(title, fontsize=15, color=NAVY, fontweight="bold", x=0.02, ha="left", y=0.965)
    fig.text(0.02, 0.93, subtitle, fontsize=9.5, color=MUTED, ha="left")
    fig.text(0.98, 0.965, f"As of {as_of}", fontsize=9, color=NAVY, ha="right", fontweight="bold")
    fig.text(0.98, 0.945, DISCLAIMER, fontsize=8, color=GOLD, ha="right", style="italic")


def _kpi(ax, label: str, value: str, sub: str = "") -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_facecolor("white")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, fill=True,
                               facecolor="white", edgecolor=GREY_LINE, linewidth=1))
    ax.text(0.05, 0.78, label.upper(), fontsize=8.5, color=MUTED, transform=ax.transAxes,
            fontweight="bold")
    ax.text(0.05, 0.34, value, fontsize=22, color=NAVY, transform=ax.transAxes, fontweight="bold")
    if sub:
        ax.text(0.05, 0.12, sub, fontsize=8, color=MUTED, transform=ax.transAxes)


def _save(fig, name: str) -> None:
    path = OUT / name
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {path.relative_to(REPO).as_posix()}")


# ---------- Data loading ----------------------------------------------------

def _load() -> dict[str, pd.DataFrame]:
    files = [
        "fact_billings", "fact_time_entries", "fact_legacy_report_inventory",
        "fact_refresh_log", "fact_requirements_backlog",
        "dim_practice", "dim_office", "dim_client", "dim_matter", "dim_date", "dim_attorney",
    ]
    return {f: pd.read_csv(DATA / f"{f}.csv") for f in files}


def _as_of(d: dict[str, pd.DataFrame]) -> str:
    dk = d["fact_refresh_log"]["DateKey"].max()
    if pd.isna(dk):
        return "n/a"
    s = str(int(dk))
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


# ---------- Pages -----------------------------------------------------------

def page_01_executive(d) -> None:
    bill = d["fact_billings"].merge(d["dim_practice"], on="PracticeKey").merge(d["dim_client"], on="ClientKey")
    legacy = d["fact_legacy_report_inventory"]
    refresh = d["fact_refresh_log"]

    total_bill = bill["BillingAmount"].sum()
    margin_pct = (bill["FeeAmount"].sum() - bill["CostAmount"].sum()) / bill["FeeAmount"].sum()
    collection_rate = bill["CashCollected"].sum() / bill["BillingAmount"].sum()
    te = d["fact_time_entries"]
    billable_pct = te.loc[te["WorkType"] == "Billable", "Hours"].sum() / te["Hours"].sum()
    active_matters = int((d["dim_matter"]["MatterStatus"] != "Closed").sum())
    migration_pct = (legacy["MigrationStatus"] == "Migrated").mean()
    refresh_rate = (refresh["RefreshStatus"] == "Success").mean()

    bill["MonthYear"] = pd.to_datetime(bill["DateKey"].astype(str), format="%Y%m%d").dt.to_period("M").dt.to_timestamp()
    monthly = bill.groupby("MonthYear")["BillingAmount"].sum().sort_index()

    margin_by_practice = (bill.groupby("PracticeName")
                          .apply(lambda x: (x["FeeAmount"].sum() - x["CostAmount"].sum()) / x["FeeAmount"].sum(), include_groups=False)
                          .sort_values(ascending=True))

    industry = bill.groupby("Industry")["BillingAmount"].sum().sort_values(ascending=True)

    top_clients = bill.groupby("ClientName")["BillingAmount"].sum().sort_values(ascending=False).head(10).iloc[::-1]

    fig = plt.figure(figsize=(13, 7.5))
    _style()
    _chrome(fig, "Executive Overview", "Firmwide performance and modernization health", _as_of(d))

    gs = fig.add_gridspec(3, 6, left=0.04, right=0.97, top=0.86, bottom=0.06, hspace=0.55, wspace=0.45)

    for i, (lbl, val, sub) in enumerate([
        ("Total Billings", f"${total_bill/1e6:,.1f}M", "Cumulative across calendar window"),
        ("Gross Margin %", f"{margin_pct:.1%}", "Fees less direct costs"),
        ("Billable %", f"{billable_pct:.1%}", "Billable / Total hours"),
        ("Collection Rate", f"{collection_rate:.1%}", "Cash / Billings"),
        ("Active Matters", f"{active_matters:,}", "Open + On Hold"),
        ("Refresh Success Rate", f"{refresh_rate:.1%}", "Certified dataset health"),
    ]):
        _kpi(fig.add_subplot(gs[0, i]), lbl, val, sub)

    ax_line = fig.add_subplot(gs[1, 0:3])
    ax_line.plot(monthly.index, monthly.values / 1e6, color=NAVY, linewidth=2.2, marker="o", markersize=4, markerfacecolor=GOLD, markeredgecolor=NAVY)
    ax_line.set_title("Billings by month ($M)", loc="left", fontsize=11)
    ax_line.yaxis.set_major_formatter(mtick.FormatStrFormatter("$%.1fM"))
    ax_line.grid(axis="y", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax_pr = fig.add_subplot(gs[1, 3:6])
    ax_pr.barh(margin_by_practice.index, margin_by_practice.values * 100, color=NAVY)
    ax_pr.set_title("Gross margin % by practice", loc="left", fontsize=11)
    ax_pr.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax_pr.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax_ind = fig.add_subplot(gs[2, 0:3])
    ax_ind.barh(industry.index, industry.values / 1e6, color=GOLD)
    ax_ind.set_title("Total billings by industry", loc="left", fontsize=11)
    ax_ind.xaxis.set_major_formatter(mtick.FormatStrFormatter("$%.0fM"))
    ax_ind.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax_cli = fig.add_subplot(gs[2, 3:6])
    ax_cli.barh(top_clients.index, top_clients.values / 1e6, color=NAVY)
    ax_cli.set_title("Top 10 clients by billings", loc="left", fontsize=11)
    ax_cli.xaxis.set_major_formatter(mtick.FormatStrFormatter("$%.1fM"))
    ax_cli.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    _save(fig, "01_executive_overview.png")


def page_02_profitability(d) -> None:
    bill = d["fact_billings"].merge(d["dim_practice"], on="PracticeKey")
    matters = d["fact_billings"].merge(d["dim_matter"], on="MatterKey")
    by_matter = (matters.groupby("MatterKey")
                 .agg(Fees=("FeeAmount", "sum"), Costs=("CostAmount", "sum"), WIP=("WIPAmount", "sum"))
                 .assign(Margin=lambda x: (x["Fees"] - x["Costs"]) / x["Fees"]))
    by_matter = by_matter[by_matter["Fees"] > 0]

    fees_pr = bill.groupby("PracticeName")["FeeAmount"].sum().sort_values()
    te = d["fact_time_entries"].merge(d["dim_practice"], on="PracticeKey")
    billable_pr = (te.loc[te["WorkType"] == "Billable"].groupby("PracticeName")["Hours"].sum() /
                   te.groupby("PracticeName")["Hours"].sum())

    fig = plt.figure(figsize=(13, 7.5))
    _style()
    _chrome(fig, "Matter & Practice Profitability", "Where the semantic model earns its keep", _as_of(d))

    gs = fig.add_gridspec(2, 2, left=0.06, right=0.97, top=0.87, bottom=0.07, hspace=0.45, wspace=0.3)

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.barh(fees_pr.index, fees_pr.values / 1e6, color=NAVY)
    ax1.set_title("Total fees by practice ($M)", loc="left", fontsize=11)
    ax1.xaxis.set_major_formatter(mtick.FormatStrFormatter("$%.0fM"))
    ax1.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax2 = fig.add_subplot(gs[0, 1])
    billable_pr_ord = billable_pr.reindex(fees_pr.index).fillna(0)
    ax2.barh(billable_pr_ord.index, billable_pr_ord.values * 100, color=GOLD)
    ax2.set_title("Billable % by practice", loc="left", fontsize=11)
    ax2.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax2.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax3 = fig.add_subplot(gs[1, :])
    sizes = (by_matter["WIP"] / by_matter["WIP"].max() * 280 + 20).clip(20, 300)
    ax3.scatter(by_matter["Fees"] / 1e3, by_matter["Margin"] * 100, s=sizes, alpha=0.45,
                color=NAVY, edgecolor="white", linewidth=0.5)
    ax3.set_title("Matter scatter: fees vs margin (bubble = WIP)", loc="left", fontsize=11)
    ax3.set_xlabel("Total fees ($K)")
    ax3.set_ylabel("Gross margin %")
    ax3.xaxis.set_major_formatter(mtick.FormatStrFormatter("$%.0fK"))
    ax3.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax3.grid(color=GREY_LINE, linewidth=0.6, alpha=0.7)

    _save(fig, "02_matter_profitability.png")


def page_03_open_pending(d) -> None:
    matters = d["dim_matter"]
    open_only = matters[matters["MatterStatus"].isin(["Open", "On Hold"])]
    by_office = open_only.groupby("OfficeName").size().sort_values(ascending=True)
    by_industry = open_only.groupby("ClientIndustry").size().sort_values(ascending=True)
    status_counts = matters["MatterStatus"].value_counts()

    fig = plt.figure(figsize=(13, 7.5))
    _style()
    _chrome(fig, "Open & Pending Cases", "Pipeline view for practice leadership", _as_of(d))

    gs = fig.add_gridspec(3, 4, left=0.05, right=0.97, top=0.87, bottom=0.07, hspace=0.55, wspace=0.45)

    _kpi(fig.add_subplot(gs[0, 0]), "Open matters", f"{int((matters['MatterStatus'] != 'Closed').sum()):,}", "Open + On Hold")
    _kpi(fig.add_subplot(gs[0, 1]), "On hold", f"{int((matters['MatterStatus'] == 'On Hold').sum()):,}", "Awaiting client action")
    _kpi(fig.add_subplot(gs[0, 2]), "Closed", f"{int((matters['MatterStatus'] == 'Closed').sum()):,}", "Historic")
    _kpi(fig.add_subplot(gs[0, 3]), "Total matters", f"{len(matters):,}", "All time")

    ax1 = fig.add_subplot(gs[1, 0:2])
    ax1.barh(by_office.index, by_office.values, color=NAVY)
    ax1.set_title("Open matters by office", loc="left", fontsize=11)
    ax1.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax2 = fig.add_subplot(gs[1, 2:4])
    ax2.barh(by_industry.index, by_industry.values, color=GOLD)
    ax2.set_title("Open matters by client industry", loc="left", fontsize=11)
    ax2.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax3 = fig.add_subplot(gs[2, :])
    ax3.bar(status_counts.index, status_counts.values, color=[NAVY, GOLD, "#5A5A55"][:len(status_counts)])
    ax3.set_title("Matter status mix", loc="left", fontsize=11)
    ax3.grid(axis="y", color=GREY_LINE, linewidth=0.6, alpha=0.7)
    for i, v in enumerate(status_counts.values):
        ax3.text(i, v, f" {int(v):,}", ha="center", va="bottom", fontsize=9, color=NAVY)

    _save(fig, "03_open_pending_cases.png")


def page_04_migration(d) -> None:
    legacy = d["fact_legacy_report_inventory"]
    refresh = d["fact_refresh_log"]
    status_counts = legacy["MigrationStatus"].value_counts()
    mig_pct = (legacy["MigrationStatus"] == "Migrated").mean()
    val_pct = (legacy["ValidationStatus"] == "Validated").mean()
    refresh_rate = (refresh["RefreshStatus"] == "Success").mean()
    health = mig_pct * 40 + val_pct * 30 + refresh_rate * 30

    by_platform = legacy.groupby(["LegacyPlatform", "Complexity"]).size().unstack(fill_value=0)

    fig = plt.figure(figsize=(13, 7.5))
    _style()
    _chrome(fig, "Legacy Report Migration Control Tower",
            "From Cognos / SSRS into Power BI on Databricks", _as_of(d))

    gs = fig.add_gridspec(3, 3, left=0.05, right=0.97, top=0.87, bottom=0.07, hspace=0.55, wspace=0.4)

    _kpi(fig.add_subplot(gs[0, 0]), "Legacy reports", f"{len(legacy):,}", "Migration backlog")
    _kpi(fig.add_subplot(gs[0, 1]), "Modernization Health Score", f"{health:.1f}",
         "0.4 migration + 0.3 validation + 0.3 refresh")
    _kpi(fig.add_subplot(gs[0, 2]), "Validation % complete", f"{val_pct:.1%}",
         "Reports with parallel-validation sign-off")

    ax1 = fig.add_subplot(gs[1, 0:2])
    ax1.pie(status_counts.values, labels=status_counts.index, startangle=90, counterclock=False,
            wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2},
            colors=[NAVY, GOLD, "#5A5A55", "#9C9C90", "#D7C28C"][:len(status_counts)],
            textprops={"fontsize": 9, "color": TEXT})
    ax1.set_title("Migration status mix", loc="left", fontsize=11)

    ax2 = fig.add_subplot(gs[1, 2])
    ax2.set_xticks([])
    ax2.set_yticks([])
    for spine in ax2.spines.values():
        spine.set_visible(False)
    ax2.set_facecolor("white")
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.add_patch(plt.Rectangle((0.0, 0.0), 1.0, 1.0, fill=True,
                                facecolor="white", edgecolor=GREY_LINE, linewidth=1))
    ax2.text(0.06, 0.82, "MIGRATION % COMPLETE", fontsize=8.5, color=MUTED, fontweight="bold")
    ax2.text(0.06, 0.55, f"{mig_pct:.1%}", fontsize=26, color=NAVY, fontweight="bold")
    ax2.add_patch(plt.Rectangle((0.06, 0.30), 0.88, 0.07, facecolor=GREY_LINE, edgecolor="none"))
    ax2.add_patch(plt.Rectangle((0.06, 0.30), 0.88 * mig_pct, 0.07, facecolor=GOLD, edgecolor="none"))
    ax2.text(0.06, 0.18, "Target: 80% by end of FY", fontsize=8, color=MUTED)

    ax3 = fig.add_subplot(gs[2, :])
    by_platform.plot.bar(stacked=True, ax=ax3, color=[NAVY, GOLD, "#5A5A55"], edgecolor="white", linewidth=0.5)
    ax3.set_title("Legacy reports by platform x complexity", loc="left", fontsize=11)
    ax3.legend(title="", frameon=False, loc="upper right")
    ax3.set_xlabel("")
    ax3.grid(axis="y", color=GREY_LINE, linewidth=0.6, alpha=0.7)
    plt.setp(ax3.get_xticklabels(), rotation=0)

    _save(fig, "04_migration_control_tower.png")


def page_05_backlog(d) -> None:
    bk = d["fact_requirements_backlog"]
    by_group = bk["StakeholderGroup"].value_counts()
    by_pri = bk["Priority"].value_counts().reindex(["P1", "P2", "P3"]).fillna(0)
    by_status = bk["RequestStatus"].value_counts()
    sla_breaches = int(bk["SLABreachFlag"].sum())
    open_count = int(bk["RequestStatus"].isin(["New", "In Discovery", "In Build", "Blocked"]).sum())

    fig = plt.figure(figsize=(13, 7.5))
    _style()
    _chrome(fig, "Stakeholder Requirements & KPI Catalog",
            "Making requirement intake measurable", _as_of(d))

    gs = fig.add_gridspec(3, 3, left=0.05, right=0.97, top=0.87, bottom=0.07, hspace=0.55, wspace=0.45)

    _kpi(fig.add_subplot(gs[0, 0]), "Open requests", f"{open_count:,}", "New + Discovery + Build + Blocked")
    _kpi(fig.add_subplot(gs[0, 1]), "SLA breaches", f"{sla_breaches:,}", "Past target date and open")
    _kpi(fig.add_subplot(gs[0, 2]), "Total backlog", f"{len(bk):,}", "All-time captured")

    ax1 = fig.add_subplot(gs[1, 0:2])
    ax1.barh(by_group.index, by_group.values, color=NAVY)
    ax1.set_title("Requests by stakeholder group", loc="left", fontsize=11)
    ax1.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax2 = fig.add_subplot(gs[1, 2])
    ax2.bar(by_pri.index, by_pri.values, color=[NAVY, GOLD, "#9C9C90"])
    ax2.set_title("Priority mix", loc="left", fontsize=11)
    ax2.grid(axis="y", color=GREY_LINE, linewidth=0.6, alpha=0.7)
    for i, v in enumerate(by_pri.values):
        ax2.text(i, v, f" {int(v):,}", ha="center", va="bottom", fontsize=9, color=NAVY)

    ax3 = fig.add_subplot(gs[2, :])
    ax3.barh(by_status.index, by_status.values, color=GOLD)
    ax3.set_title("Status mix", loc="left", fontsize=11)
    ax3.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    _save(fig, "05_stakeholder_backlog.png")


def page_06_refresh(d) -> None:
    rl = d["fact_refresh_log"].copy()
    rl["Date"] = pd.to_datetime(rl["DateKey"].astype(str), format="%Y%m%d")
    rate = (rl["RefreshStatus"] == "Success").mean()
    failed = int((rl["RefreshStatus"] == "Failed").sum())
    avg_dur = rl["DurationMinutes"].mean()

    duration_by_date = rl.groupby("Date")["DurationMinutes"].mean()
    failures = rl[rl["RefreshStatus"] == "Failed"]
    failure_by_cat = failures["FailureCategory"].value_counts()
    failure_by_dataset = failures["DatasetName"].value_counts().head(8).iloc[::-1]

    fig = plt.figure(figsize=(13, 7.5))
    _style()
    _chrome(fig, "Data Quality & Refresh Monitor",
            "Production readiness signal for the certified dataset", _as_of(d))

    gs = fig.add_gridspec(3, 3, left=0.05, right=0.97, top=0.87, bottom=0.07, hspace=0.55, wspace=0.4)

    _kpi(fig.add_subplot(gs[0, 0]), "Refresh success rate", f"{rate:.1%}", "Across logged refreshes")
    _kpi(fig.add_subplot(gs[0, 1]), "Failed refreshes", f"{failed:,}", "Total failures captured")
    _kpi(fig.add_subplot(gs[0, 2]), "Avg duration", f"{avg_dur:.1f} min", "Across all datasets")

    ax1 = fig.add_subplot(gs[1, :])
    ax1.plot(duration_by_date.index, duration_by_date.values, color=NAVY, linewidth=1.5)
    ax1.fill_between(duration_by_date.index, duration_by_date.values, color=NAVY, alpha=0.08)
    ax1.set_title("Average refresh duration over time (minutes)", loc="left", fontsize=11)
    ax1.grid(color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax2 = fig.add_subplot(gs[2, 0])
    if not failure_by_cat.empty:
        ax2.barh(failure_by_cat.index, failure_by_cat.values, color=GOLD)
    ax2.set_title("Failures by category", loc="left", fontsize=11)
    ax2.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax3 = fig.add_subplot(gs[2, 1:3])
    if not failure_by_dataset.empty:
        ax3.barh(failure_by_dataset.index, failure_by_dataset.values, color=NAVY)
    ax3.set_title("Top datasets by failure count", loc="left", fontsize=11)
    ax3.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    _save(fig, "06_refresh_monitor.png")


def page_07_rls(d) -> None:
    matters = d["dim_matter"]
    bill = d["fact_billings"].merge(d["dim_office"], on="OfficeKey")
    bk = d["fact_requirements_backlog"]

    firmwide_bill = bill["BillingAmount"].sum()
    chicago_bill = bill.loc[bill["OfficeName"] == "Chicago", "BillingAmount"].sum()
    chicago_matters = int((matters["OfficeName"] == "Chicago").sum())
    firmwide_matters = len(matters)
    finance_bk = int((bk["StakeholderGroup"] == "Finance").sum())

    fig = plt.figure(figsize=(13, 7.5))
    _style()
    _chrome(fig, "RLS / Office Security Demo",
            "Ethical-walls and office-scoped access via three sample roles", _as_of(d))

    gs = fig.add_gridspec(3, 4, left=0.05, right=0.97, top=0.87, bottom=0.07, hspace=0.55, wspace=0.4)

    _kpi(fig.add_subplot(gs[0, 0]), "Firmwide billings", f"${firmwide_bill/1e6:,.1f}M", "Default role / no filter")
    _kpi(fig.add_subplot(gs[0, 1]), "Chicago Office Demo", f"${chicago_bill/1e6:,.1f}M", "OfficeName = 'Chicago'")
    _kpi(fig.add_subplot(gs[0, 2]), "OfficeKey = 1 sample", f"${chicago_bill/1e6:,.1f}M", "Surrogate-key alternative")
    _kpi(fig.add_subplot(gs[0, 3]), "Finance Stakeholder", f"{finance_bk:,}", "Backlog rows visible")

    ax1 = fig.add_subplot(gs[1, 0:2])
    labels = ["Firmwide", "Chicago Office Demo", "OfficeKey = 1"]
    vals = [firmwide_bill, chicago_bill, chicago_bill]
    ax1.barh(labels, [v / 1e6 for v in vals], color=[NAVY, GOLD, GOLD])
    ax1.set_title("Visible billings by role ($M)", loc="left", fontsize=11)
    ax1.xaxis.set_major_formatter(mtick.FormatStrFormatter("$%.0fM"))
    ax1.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax2 = fig.add_subplot(gs[1, 2:4])
    labels2 = ["Firmwide", "Chicago Office Demo", "OfficeKey = 1"]
    vals2 = [firmwide_matters, chicago_matters, chicago_matters]
    ax2.barh(labels2, vals2, color=[NAVY, GOLD, GOLD])
    ax2.set_title("Visible matters by role", loc="left", fontsize=11)
    ax2.grid(axis="x", color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax3 = fig.add_subplot(gs[2, :])
    ax3.set_xticks([])
    ax3.set_yticks([])
    for spine in ax3.spines.values():
        spine.set_visible(False)
    ax3.set_facecolor("white")
    ax3.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax3.transAxes, fill=True,
                                facecolor="white", edgecolor=GREY_LINE, linewidth=1))
    ax3.text(0.02, 0.78,
             "Modeling -> View as roles: confirm Chicago Office Demo and OfficeKey = 1 return the same slice.",
             fontsize=10, color=TEXT, transform=ax3.transAxes, fontweight="bold")
    ax3.text(0.02, 0.55,
             "Production RLS would add Practice Leadership, Marketing / BD, Firm Leadership,",
             fontsize=9.5, color=MUTED, transform=ax3.transAxes)
    ax3.text(0.02, 0.40,
             "and a dynamic Office role driven by an office_user_map table joined on USERPRINCIPALNAME.",
             fontsize=9.5, color=MUTED, transform=ax3.transAxes)
    ax3.text(0.02, 0.15,
             "See docs/AI_GOVERNANCE.md and docs/DEPLOYMENT.md for the rollout sequence.",
             fontsize=9, color=GOLD, transform=ax3.transAxes, style="italic")

    _save(fig, "07_rls_demo.png")


def page_08_visual_lab(d) -> None:
    bill = d["fact_billings"].merge(d["dim_practice"], on="PracticeKey")
    legacy = d["fact_legacy_report_inventory"]

    practice_bill = bill.groupby("PracticeName")["BillingAmount"].sum().sort_values(ascending=False)
    status_counts = legacy["MigrationStatus"].value_counts()

    matters = d["fact_billings"].merge(d["dim_matter"], on="MatterKey")
    by_matter = (matters.groupby("MatterKey")
                 .agg(Fees=("FeeAmount", "sum"), Costs=("CostAmount", "sum"), WIP=("WIPAmount", "sum"))
                 .assign(Margin=lambda x: (x["Fees"] - x["Costs"]) / x["Fees"]))
    by_matter = by_matter[by_matter["Fees"] > 0].sample(min(200, len(by_matter)), random_state=42)

    funnel_order = ["Not Started", "In Discovery", "In Build", "Parallel Validation", "Migrated", "Retired"]
    funnel = legacy["MigrationStatus"].value_counts().reindex(funnel_order).dropna()

    fig = plt.figure(figsize=(13, 7.5))
    _style()
    _chrome(fig, "Visual lab & motion",
            "Native chart variety + bookmark / page-transition guidance", _as_of(d))

    gs = fig.add_gridspec(2, 2, left=0.05, right=0.97, top=0.87, bottom=0.07, hspace=0.4, wspace=0.3)

    ax1 = fig.add_subplot(gs[0, 0])
    norm = practice_bill / practice_bill.sum()
    palette = [NAVY, GOLD, "#5A5A55", "#9C9C90", "#D7C28C", "#7A7A6E", "#3F5A78", "#A47A2E"]
    items = list(norm.items())
    rows = [[], []]
    row_totals = [0.0, 0.0]
    for name, val in items:
        idx = 0 if row_totals[0] <= row_totals[1] else 1
        rows[idx].append((name, val))
        row_totals[idx] += val
    color_idx = 0
    for row_i, (row, total) in enumerate(zip(rows, row_totals)):
        if total == 0:
            continue
        y0 = 0.0 if row_i == 0 else 0.5
        x = 0.0
        for name, val in row:
            rect_w = val / total
            ax1.add_patch(plt.Rectangle((x, y0), rect_w, 0.5, facecolor=palette[color_idx % len(palette)],
                                        edgecolor="white", linewidth=1.5))
            ax1.text(x + rect_w / 2, y0 + 0.25,
                     f"{name}\n${practice_bill[name] / 1e6:,.0f}M",
                     ha="center", va="center", fontsize=8.5, color="white", fontweight="bold")
            x += rect_w
            color_idx += 1
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.set_xticks([])
    ax1.set_yticks([])
    for s in ax1.spines.values():
        s.set_visible(False)
    ax1.set_title("Treemap: billings by practice", loc="left", fontsize=11)

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.pie(status_counts.values, labels=status_counts.index, startangle=90, counterclock=False,
            wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2},
            colors=palette[:len(status_counts)],
            textprops={"fontsize": 9, "color": TEXT})
    ax2.set_title("Donut: legacy reports by migration status", loc="left", fontsize=11)

    ax3 = fig.add_subplot(gs[1, 0])
    sizes = (by_matter["WIP"] / by_matter["WIP"].max() * 220 + 20).clip(20, 240)
    ax3.scatter(by_matter["Fees"] / 1e3, by_matter["Margin"] * 100, s=sizes, alpha=0.45,
                color=NAVY, edgecolor="white", linewidth=0.5)
    ax3.set_title("Scatter: matters (fees vs margin, size = WIP)", loc="left", fontsize=11)
    ax3.xaxis.set_major_formatter(mtick.FormatStrFormatter("$%.0fK"))
    ax3.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax3.grid(color=GREY_LINE, linewidth=0.6, alpha=0.7)

    ax4 = fig.add_subplot(gs[1, 1])
    for s in ax4.spines.values():
        s.set_visible(False)
    ax4.set_xticks([])
    ax4.set_yticks([])
    ax4.set_xlim(-1, 1)
    ax4.set_ylim(-0.5, len(funnel))
    max_w = funnel.max() if funnel.max() > 0 else 1
    for i, (name, val) in enumerate(funnel.items()):
        w = (val / max_w) * 0.9
        ax4.add_patch(plt.Rectangle((-w, len(funnel) - i - 1), w * 2, 0.7,
                                    facecolor=palette[i % len(palette)], edgecolor="white", linewidth=1.5))
        ax4.text(0, len(funnel) - i - 0.65, f"{name}: {int(val)}",
                 ha="center", va="center", fontsize=9, color="white", fontweight="bold")
    ax4.set_title("Funnel: migration stage volumes", loc="left", fontsize=11)

    _save(fig, "08_visual_lab.png")


def main() -> int:
    if not DATA.is_dir():
        print(f"missing data dir {DATA}; run generate_sidley_pbip.py first", flush=True)
        return 1
    d = _load()
    page_01_executive(d)
    page_02_profitability(d)
    page_03_open_pending(d)
    page_04_migration(d)
    page_05_backlog(d)
    page_06_refresh(d)
    page_07_rls(d)
    page_08_visual_lab(d)
    print(f"\n{len(list(OUT.glob('*.png')))} PNGs written to {OUT.relative_to(REPO).as_posix()}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
