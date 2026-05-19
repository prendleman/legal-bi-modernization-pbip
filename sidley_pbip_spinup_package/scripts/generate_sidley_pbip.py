"""Sidley BI Modernization Demo - PBIP scaffold generator.

Generates curated CSV "gold" extracts, a PBIP project with a TMSL semantic
model (calc groups, hierarchies, formatted measures), PBIR report visuals
(cards, line, column, bar, scatter, treemap, donut, funnel, tables), Databricks artifacts
(SQL DDL + PySpark notebook), and a data quality report. Optionally pushes
the gold extracts into Unity Catalog via `--databricks`.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import shutil
import sys
import uuid
import textwrap
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from databricks_artifacts import write_gold_ddl, write_pyspark_notebook
from databricks_client import (
    DatabricksClient,
    GOLD_TABLES,
    configure_logging,
    load_config,
)
from pbir_visuals import emit_all_page_visuals, page_folder_id


PROJECT_NAME = "Sidley_BI_Modernization_Demo"
CUSTOM_THEME_FILE = "SidleyCom.json"
CUSTOM_THEME_DISPLAY_NAME = "Sidley Com"
# themeCollection.reportVersionAtImport must be an object (not a string) or Desktop may drop
# the registered custom theme when saving as PBIX. Align with PBIR schemas used in this kit.
THEME_IMPORT_VERSIONS = {"visual": "2.4.0", "report": "1.3.0", "page": "1.4.0"}
REPORT_ASSETS_DIR = Path(__file__).resolve().parent / "report_assets"
DEFAULT_START = date(2023, 1, 1)


def load_sidley_public_attorney_names() -> Tuple[List[str], List[dict]]:
    """Public leadership names from `sidley_public_attorney_names.json` (Sidley.com sources)."""
    path = REPORT_ASSETS_DIR / "sidley_public_attorney_names.json"
    if not path.is_file():
        return [], []
    data = json.loads(path.read_text(encoding="utf-8"))
    names = [str(x).strip() for x in data.get("display_names", []) if str(x).strip()]
    return names, list(data.get("sources", []))


def sidley_attorney_display_name(index_one_based: int, pool: List[str]) -> str:
    """Unique `AttorneyName` for row *index_one_based* (1..N). Pool is public-directory names; overflow gets a demo suffix."""
    if not pool:
        return f"Attorney {index_one_based:03d}"
    if index_one_based <= len(pool):
        return pool[index_one_based - 1]
    base = pool[(index_one_based - 1) % len(pool)]
    return f"{base} (demo roster {index_one_based:03d})"
DEFAULT_END = date(2026, 4, 30)
DEFAULT_TIME_ENTRY_ROWS = 26000
# Lighter PBIX / email attachment: fewer time-entry rows (still exercises joins + model).
INTERVIEW_TIME_ENTRY_ROWS = 4500
DEFAULT_LANDING_PAGE_KEY = "Executive_Overview"


# ---------------------------------------------------------------------------
# tiny IO helpers
# ---------------------------------------------------------------------------

def yyyymmdd(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def json_dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def safe_abs(p: Path) -> str:
    return str(p.resolve()).replace("\\", "\\\\")


# ---------------------------------------------------------------------------
# US federal holidays (lightweight - no external deps)
# ---------------------------------------------------------------------------

def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """nth (1-based) `weekday` of `month` in `year`. Mon=0..Sun=6."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        next_first = date(year + 1, 1, 1)
    else:
        next_first = date(year, month + 1, 1)
    last = next_first - timedelta(days=1)
    offset = (last.weekday() - weekday) % 7
    return last - timedelta(days=offset)


def us_federal_holidays(year: int) -> List[date]:
    return [
        date(year, 1, 1),
        _nth_weekday(year, 1, 0, 3),     # MLK Day
        _nth_weekday(year, 2, 0, 3),     # Presidents' Day
        _last_weekday(year, 5, 0),       # Memorial Day
        date(year, 6, 19),               # Juneteenth
        date(year, 7, 4),
        _nth_weekday(year, 9, 0, 1),     # Labor Day
        _nth_weekday(year, 10, 0, 2),    # Columbus Day
        date(year, 11, 11),
        _nth_weekday(year, 11, 3, 4),    # Thanksgiving
        date(year, 12, 25),
    ]


# ---------------------------------------------------------------------------
# Power Query M expressions
# ---------------------------------------------------------------------------

_M_PARAMETERS: List[Tuple[str, str, str]] = [
    ("pDataSource",       "CSV",                                    "Text"),
    ("pDatabricksHost",   "adb-0000000000000000.0.azuredatabricks.net", "Text"),
    ("pDatabricksHttpPath", "/sql/1.0/warehouses/REPLACE_WAREHOUSE_ID", "Text"),
    ("pDatabricksCatalog", "sidley_demo",                            "Text"),
    ("pDatabricksSchema",  "gold",                                   "Text"),
    ("pCsvRoot",           "REPLACE_AT_GENERATION",                  "Text"),
]


def m_parameter_expression(value: str, ptype: str) -> str:
    return (
        f'"{value}" meta [IsParameterQuery=true, Type="{ptype}", '
        f'IsParameterQueryRequired=true]'
    )


def _m_catalog_item_name_expression(table_name: str) -> str:
    """M expression that evaluates to the logical table name without embedding the full name as one literal.

    Power Query can mis-detect a circular dependency when the partition query name matches the
    ``Item = \"...\"`` string inside the same query (refresh: cyclic reference on that table).
    Building the name with ``Text.Combine`` avoids that self-match in the M text.
    """
    parts = table_name.split("_")
    if len(parts) == 1:
        return f'"{table_name}"'
    inner = ", ".join(f'"{p}"' for p in parts)
    return f'Text.Combine({{{inner}}}, "_")'


def m_table_expression(table_name: str, csv_path: Path, type_steps: str) -> str:
    """Branching M: read from Databricks SQL Warehouse if pDataSource = 'Databricks',
    otherwise read the local CSV path captured at generation time."""
    csv_literal = safe_abs(csv_path)
    nav_item = _m_catalog_item_name_expression(table_name)
    return textwrap.dedent(
        f"""\
        let
            CsvPath = "{csv_literal}",
            NavItem = {nav_item},
            FromDatabricks = () =>
                let
                    Source = Databricks.Catalogs(pDatabricksHost, pDatabricksHttpPath, [Catalog = pDatabricksCatalog, Database = pDatabricksSchema]),
                    Table = Source{{[Item = NavItem, Schema = pDatabricksSchema, Kind = "Table"]}}[Data]
                in
                    Table,
            FromCsv = () =>
                let
                    Source = Csv.Document(File.Contents(CsvPath), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
                    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
                    ChangedType = Table.TransformColumnTypes(PromotedHeaders, {type_steps})
                in
                    ChangedType,
            Result = if pDataSource = "Databricks" then FromDatabricks() else FromCsv()
        in
            Result"""
    )


# ---------------------------------------------------------------------------
# data generation
# ---------------------------------------------------------------------------

@dataclass
class GeneratorOptions:
    out_dir: Path
    seed: int = 42
    time_entry_rows: int = DEFAULT_TIME_ENTRY_ROWS
    start: date = DEFAULT_START
    end: date = DEFAULT_END


def generate_dim_date(start: date, end: date) -> List[dict]:
    holiday_set: set = set()
    for year in range(start.year, end.year + 1):
        holiday_set.update(us_federal_holidays(year))

    rows = []
    d = start
    while d <= end:
        rows.append({
            "DateKey": yyyymmdd(d),
            "Date": d.isoformat(),
            "Year": d.year,
            "Quarter": f"Q{((d.month - 1) // 3) + 1}",
            "MonthNumber": d.month,
            "MonthName": d.strftime("%B"),
            "MonthYear": d.strftime("%Y-%m"),
            "WeekdayName": d.strftime("%A"),
            "IsWeekend": 1 if d.weekday() >= 5 else 0,
            "IsMonthEnd": 1 if (d + timedelta(days=1)).day == 1 else 0,
            "IsHoliday": 1 if d in holiday_set else 0,
            # Sidley operates on a calendar fiscal year; FiscalYear == Year here.
            # Columns are still emitted so a different fiscal calendar can be
            # plugged in upstream without rewiring the model.
            "FiscalYear": d.year,
            "FiscalQuarter": f"FY{d.year} Q{((d.month - 1) // 3) + 1}",
            "FiscalMonth": d.month,
        })
        d += timedelta(days=1)
    return rows


def generate_data(opts: GeneratorOptions) -> Dict[str, List[dict]]:
    rng = random.Random(opts.seed)

    dim_date = generate_dim_date(opts.start, opts.end)

    offices = [
        (1, "Chicago",       "Midwest",   "US", "Central"),
        (2, "New York",      "Northeast", "US", "Eastern"),
        (3, "Washington DC", "Northeast", "US", "Eastern"),
        (4, "Los Angeles",   "West",      "US", "Pacific"),
        (5, "Dallas",        "South",     "US", "Central"),
        (6, "Miami",         "South",     "US", "Eastern"),
        (7, "London",        "Europe",    "UK", "GMT"),
    ]
    dim_office = [
        {"OfficeKey": k, "OfficeName": n, "Region": r, "Country": c, "TimeZoneGroup": tz}
        for k, n, r, c, tz in offices
    ]

    practices = [
        (1, "Corporate",              "Transactional"),
        (2, "Litigation",             "Disputes"),
        (3, "Intellectual Property",  "Specialty"),
        (4, "Real Estate",            "Transactional"),
        (5, "Tax",                    "Advisory"),
        (6, "Regulatory",             "Advisory"),
        (7, "Labor & Employment",     "Advisory"),
        (8, "Private Equity",         "Transactional"),
    ]
    dim_practice = [
        {"PracticeKey": k, "PracticeName": n, "PracticeGroup": g}
        for k, n, g in practices
    ]

    industries = ["Financial Services", "Technology", "Healthcare", "Manufacturing",
                  "Real Estate", "Energy", "Retail", "Private Equity"]
    tiers = ["Strategic", "Growth", "Core", "Emerging"]
    dim_client = []
    for i in range(1, 181):
        dim_client.append({
            "ClientKey": i,
            "ClientName": f"Client {i:03d}",
            "Industry": rng.choice(industries),
            "ClientTier": rng.choices(tiers, weights=[12, 22, 46, 20])[0],
            "RiskLevel": rng.choices(["Low", "Medium", "High"], weights=[55, 35, 10])[0],
            "ClientStatus": rng.choices(["Active", "Watch", "Dormant"], weights=[82, 12, 6])[0],
        })

    attorney_levels = ["Associate", "Senior Associate", "Counsel", "Partner"]
    base_rates = {"Associate": 425, "Senior Associate": 625, "Counsel": 780, "Partner": 1050}
    sidley_name_pool, _sidley_sources = load_sidley_public_attorney_names()
    if not sidley_name_pool:
        logging.getLogger("generate_sidley_pbip").warning(
            "Missing %s — using generic Attorney ### labels.",
            REPORT_ASSETS_DIR / "sidley_public_attorney_names.json",
        )
    dim_attorney = []
    for i in range(1, 121):
        level = rng.choices(attorney_levels, weights=[45, 25, 10, 20])[0]
        rate = base_rates[level] + rng.randint(-75, 125)
        office = rng.choice(dim_office)
        practice = rng.choice(dim_practice)
        dim_attorney.append({
            "AttorneyKey": i,
            "AttorneyName": sidley_attorney_display_name(i, sidley_name_pool),
            "AttorneyLevel": level,
            "OfficeKey": office["OfficeKey"],
            "PracticeKey": practice["PracticeKey"],
            "StandardRate": rate,
            "IsActive": 1,
        })

    matter_types = ["M&A", "Commercial Litigation", "IP Portfolio", "Real Estate Deal",
                    "Tax Advisory", "Regulatory Review", "Employment Counsel", "Fund Formation"]
    partner_keys = [a["AttorneyKey"] for a in dim_attorney if a["AttorneyLevel"] == "Partner"]
    attorney_by_key = {a["AttorneyKey"]: a for a in dim_attorney}
    dim_matter = []
    for i in range(1, 451):
        client = rng.choice(dim_client)
        practice = rng.choice(dim_practice)
        office = rng.choice(dim_office)
        open_date = opts.start + timedelta(days=rng.randint(0, 950))
        status = rng.choices(["Open", "Closed", "On Hold"], weights=[68, 27, 5])[0]
        close_date = "" if status == "Open" else (
            open_date + timedelta(days=rng.randint(60, 540))
        ).isoformat()
        lead_key = rng.choice(partner_keys)
        lead = attorney_by_key[lead_key]
        dim_matter.append({
            "MatterKey": i,
            "MatterNumber": f"M-{2020 + (i % 6)}-{i:05d}",
            "MatterName": f"{practice['PracticeName']} Matter {i:03d}",
            "ClientKey": client["ClientKey"],
            "OfficeKey": office["OfficeKey"],
            "PracticeKey": practice["PracticeKey"],
            "MatterType": rng.choice(matter_types),
            "MatterStatus": status,
            "OpenDate": open_date.isoformat(),
            "CloseDate": close_date,
            "LeadPartnerAttorneyKey": lead_key,
            # Denormalized labels: matter-level visuals without dim_matter→dim_* relationships (avoids ambiguous paths).
            "OfficeName": office["OfficeName"],
            "ClientName": client["ClientName"],
            "ClientIndustry": client["Industry"],
            "LeadAttorneyName": lead["AttorneyName"],
        })

    months = []
    cur = opts.start.replace(day=1)
    while cur <= opts.end:
        months.append(cur)
        cur = date(cur.year + 1, 1, 1) if cur.month == 12 else date(cur.year, cur.month + 1, 1)

    fact_billings = []
    bill_id = 1
    for m in months:
        for matter in rng.sample(dim_matter, k=min(165, len(dim_matter))):
            if rng.random() < 0.48:
                continue
            practice_factor = 1 + (matter["PracticeKey"] * 0.025)
            billed_hours = round(rng.uniform(8, 190) * practice_factor, 1)
            avg_rate = rng.uniform(425, 1050)
            fee = round(billed_hours * avg_rate * rng.uniform(0.82, 1.07), 2)
            cost = round(fee * rng.uniform(0.38, 0.68), 2)
            billing_amount = round(fee + rng.uniform(0, 8000), 2)
            cash = round(billing_amount * rng.uniform(0.72, 1.03), 2)
            ar = max(0, round(billing_amount - cash + rng.uniform(-2500, 6500), 2))
            wip = round(rng.uniform(0, 45000), 2)
            fact_billings.append({
                "BillingEventKey": bill_id,
                "DateKey": yyyymmdd(m),
                "MatterKey": matter["MatterKey"],
                "ClientKey": matter["ClientKey"],
                "OfficeKey": matter["OfficeKey"],
                "PracticeKey": matter["PracticeKey"],
                "BilledHours": billed_hours,
                "FeeAmount": fee,
                "CostAmount": cost,
                "BillingAmount": billing_amount,
                "CashCollected": cash,
                "AROutstanding": ar,
                "WIPAmount": wip,
                "DiscountAmount": round(fee * rng.uniform(0, 0.08), 2),
            })
            bill_id += 1

    work_types = ["Billable", "Business Development", "Pro Bono", "Admin"]
    all_dates = [opts.start + timedelta(days=i) for i in range((opts.end - opts.start).days + 1)]
    fact_time_entries = []
    for tid in range(1, opts.time_entry_rows + 1):
        attorney = rng.choice(dim_attorney)
        matter = rng.choice(dim_matter)
        d = rng.choice(all_dates)
        wt = rng.choices(work_types, weights=[78, 8, 7, 7])[0]
        hrs = round(rng.uniform(0.4, 8.5), 1)
        fact_time_entries.append({
            "TimeEntryKey": tid,
            "DateKey": yyyymmdd(d),
            "AttorneyKey": attorney["AttorneyKey"],
            "MatterKey": matter["MatterKey"],
            "OfficeKey": attorney["OfficeKey"],
            "PracticeKey": attorney["PracticeKey"],
            "WorkType": wt,
            "Hours": hrs,
            "StandardRate": attorney["StandardRate"],
            "NarrativeQualityScore": rng.randint(1, 5),
        })

    platforms = ["Cognos", "SSRS", "Excel", "Access", "Tableau"]
    statuses = ["Not Started", "In Discovery", "In Build", "Parallel Validation", "Migrated", "Retired"]
    validations = ["Not Started", "In Progress", "Validated", "Exception"]
    stakeholder_groups = ["Finance", "Marketing / BD", "Practice Leadership",
                          "Operations", "HR", "Firm Leadership"]
    fact_legacy_report_inventory = []
    for i in range(1, 151):
        platform = rng.choices(platforms, weights=[35, 31, 15, 6, 13])[0]
        status = rng.choices(statuses, weights=[13, 16, 22, 16, 24, 9])[0]
        val = "Validated" if status in ["Migrated", "Retired"] and rng.random() > 0.23 else rng.choice(validations)
        office = rng.choice(dim_office)
        practice = rng.choice(dim_practice)
        fact_legacy_report_inventory.append({
            "LegacyReportKey": i,
            "LegacyReportName": f"{platform} Report {i:03d}",
            "LegacyPlatform": platform,
            "OwningStakeholderGroup": rng.choice(stakeholder_groups),
            "OwningOfficeKey": office["OfficeKey"],
            "OwningPracticeKey": practice["PracticeKey"],
            "Complexity": rng.choices(["Low", "Medium", "High"], weights=[36, 44, 20])[0],
            "MigrationStatus": status,
            "ValidationStatus": val,
            "EstimatedHoursRemaining": rng.randint(0, 120) if status not in ["Migrated", "Retired"] else 0,
            "UsageScore": rng.randint(1, 100),
            "TargetWorkspace": rng.choice(["Finance Analytics", "Marketing Analytics",
                                            "Firm Leadership", "Practice Analytics"]),
            "ReplacementReportName": f"Power BI Replacement {i:03d}",
        })

    req_statuses = ["New", "In Discovery", "In Build", "Blocked", "Complete"]
    priorities = ["P1", "P2", "P3"]
    product_managers = [
        "Jordan Lee", "Sam Rivera", "Priya Shah", "Alex Nguyen", "Morgan Ellis",
        "Casey Wu", "Riley Ortiz", "Taylor Kim",
    ]
    fact_requirements_backlog = []
    for i in range(1, 111):
        office = rng.choice(dim_office)
        practice = rng.choice(dim_practice)
        created = opts.start + timedelta(days=rng.randint(500, 1180))
        target = created + timedelta(days=rng.randint(14, 90))
        status = rng.choices(req_statuses, weights=[12, 20, 27, 9, 32])[0]
        fact_requirements_backlog.append({
            "RequirementKey": i,
            "RequestTitle": f"KPI / Dashboard Request {i:03d}",
            "ProductManager": rng.choice(product_managers),
            "EpicId": f"FIRM-{rng.randint(1200, 8999)}",
            "StakeholderGroup": rng.choice(stakeholder_groups),
            "OfficeKey": office["OfficeKey"],
            "PracticeKey": practice["PracticeKey"],
            "KPIArea": rng.choice(["Realization", "WIP", "Collections", "Profitability",
                                    "Client Growth", "Matter Pipeline", "Legacy Migration"]),
            "Priority": rng.choices(priorities, weights=[24, 51, 25])[0],
            "RequestStatus": status,
            "CreatedDate": created.isoformat(),
            "TargetDate": target.isoformat(),
            "SLABreachFlag": 1 if status != "Complete" and target < date(2026, 4, 1) and rng.random() > 0.45 else 0,
            "AcceptanceCriteria": "Metric definition approved, visual validated, and owner signoff captured.",
        })

    datasets = ["Firmwide Finance Model", "Matter Profitability Model",
                "Legacy Migration Control Tower", "Marketing BD Model", "Refresh Monitor"]
    fact_refresh_log = []
    recent_dates = all_dates[-540:] if len(all_dates) >= 540 else all_dates
    for i in range(1, 751):
        d = rng.choice(recent_dates)
        dataset = rng.choice(datasets)
        success = rng.random() > 0.075
        fact_refresh_log.append({
            "RefreshLogKey": i,
            "DateKey": yyyymmdd(d),
            "DatasetName": dataset,
            "RefreshStatus": "Success" if success else "Failed",
            "DurationMinutes": round(rng.uniform(2, 38) if success else rng.uniform(10, 70), 1),
            "RowsProcessed": rng.randint(2000, 220000) if success else rng.randint(0, 12000),
            "FailureCategory": "" if success else rng.choice(
                ["Gateway", "Credential", "Schema Drift", "Timeout", "Source Unavailable"]
            ),
        })

    return {
        "dim_date": dim_date,
        "dim_office": dim_office,
        "dim_practice": dim_practice,
        "dim_client": dim_client,
        "dim_attorney": dim_attorney,
        "dim_matter": dim_matter,
        "fact_billings": fact_billings,
        "fact_time_entries": fact_time_entries,
        "fact_legacy_report_inventory": fact_legacy_report_inventory,
        "fact_requirements_backlog": fact_requirements_backlog,
        "fact_refresh_log": fact_refresh_log,
    }


# ---------------------------------------------------------------------------
# table specs (single source of truth for column types - drives bim + DDL)
# ---------------------------------------------------------------------------

def build_table_specs(data_dir: Path) -> Dict[str, Dict]:
    return {
        "dim_date": {
            "file": data_dir / "dim_date.csv",
            "types": (
                '{{"DateKey", Int64.Type}, {"Date", type date}, {"Year", Int64.Type}, '
                '{"Quarter", type text}, {"MonthNumber", Int64.Type}, {"MonthName", type text}, '
                '{"MonthYear", type text}, {"WeekdayName", type text}, {"IsWeekend", Int64.Type}, '
                '{"IsMonthEnd", Int64.Type}, {"IsHoliday", Int64.Type}, {"FiscalYear", Int64.Type}, '
                '{"FiscalQuarter", type text}, {"FiscalMonth", Int64.Type}}'
            ),
            "columns": [
                ("DateKey", "int64"), ("Date", "dateTime"), ("Year", "int64"),
                ("Quarter", "string"), ("MonthNumber", "int64"), ("MonthName", "string"),
                ("MonthYear", "string"), ("WeekdayName", "string"), ("IsWeekend", "int64"),
                ("IsMonthEnd", "int64"), ("IsHoliday", "int64"), ("FiscalYear", "int64"),
                ("FiscalQuarter", "string"), ("FiscalMonth", "int64"),
            ],
            "is_date_table": True,
        },
        "dim_office": {
            "file": data_dir / "dim_office.csv",
            "types": (
                '{{"OfficeKey", Int64.Type}, {"OfficeName", type text}, {"Region", type text}, '
                '{"Country", type text}, {"TimeZoneGroup", type text}}'
            ),
            "columns": [
                ("OfficeKey", "int64"), ("OfficeName", "string"), ("Region", "string"),
                ("Country", "string"), ("TimeZoneGroup", "string"),
            ],
        },
        "dim_practice": {
            "file": data_dir / "dim_practice.csv",
            "types": (
                '{{"PracticeKey", Int64.Type}, {"PracticeName", type text}, '
                '{"PracticeGroup", type text}}'
            ),
            "columns": [
                ("PracticeKey", "int64"), ("PracticeName", "string"), ("PracticeGroup", "string"),
            ],
        },
        "dim_client": {
            "file": data_dir / "dim_client.csv",
            "types": (
                '{{"ClientKey", Int64.Type}, {"ClientName", type text}, {"Industry", type text}, '
                '{"ClientTier", type text}, {"RiskLevel", type text}, {"ClientStatus", type text}}'
            ),
            "columns": [
                ("ClientKey", "int64"), ("ClientName", "string"), ("Industry", "string"),
                ("ClientTier", "string"), ("RiskLevel", "string"), ("ClientStatus", "string"),
            ],
        },
        "dim_attorney": {
            "file": data_dir / "dim_attorney.csv",
            "types": (
                '{{"AttorneyKey", Int64.Type}, {"AttorneyName", type text}, '
                '{"AttorneyLevel", type text}, {"OfficeKey", Int64.Type}, '
                '{"PracticeKey", Int64.Type}, {"StandardRate", Int64.Type}, '
                '{"IsActive", Int64.Type}}'
            ),
            "columns": [
                ("AttorneyKey", "int64"), ("AttorneyName", "string"),
                ("AttorneyLevel", "string"), ("OfficeKey", "int64"),
                ("PracticeKey", "int64"), ("StandardRate", "int64"), ("IsActive", "int64"),
            ],
        },
        "dim_matter": {
            "file": data_dir / "dim_matter.csv",
            "types": (
                '{{"MatterKey", Int64.Type}, {"MatterNumber", type text}, '
                '{"MatterName", type text}, {"ClientKey", Int64.Type}, '
                '{"OfficeKey", Int64.Type}, {"PracticeKey", Int64.Type}, '
                '{"MatterType", type text}, {"MatterStatus", type text}, '
                '{"OpenDate", type date}, {"CloseDate", type text}, '
                '{"LeadPartnerAttorneyKey", Int64.Type}, '
                '{"OfficeName", type text}, {"ClientName", type text}, '
                '{"ClientIndustry", type text}, {"LeadAttorneyName", type text}}'
            ),
            "columns": [
                ("MatterKey", "int64"), ("MatterNumber", "string"), ("MatterName", "string"),
                ("ClientKey", "int64"), ("OfficeKey", "int64"), ("PracticeKey", "int64"),
                ("MatterType", "string"), ("MatterStatus", "string"), ("OpenDate", "dateTime"),
                ("CloseDate", "string"), ("LeadPartnerAttorneyKey", "int64"),
                ("OfficeName", "string"), ("ClientName", "string"), ("ClientIndustry", "string"),
                ("LeadAttorneyName", "string"),
            ],
        },
        "fact_billings": {
            "file": data_dir / "fact_billings.csv",
            "types": (
                '{{"BillingEventKey", Int64.Type}, {"DateKey", Int64.Type}, '
                '{"MatterKey", Int64.Type}, {"ClientKey", Int64.Type}, '
                '{"OfficeKey", Int64.Type}, {"PracticeKey", Int64.Type}, '
                '{"BilledHours", type number}, {"FeeAmount", type number}, '
                '{"CostAmount", type number}, {"BillingAmount", type number}, '
                '{"CashCollected", type number}, {"AROutstanding", type number}, '
                '{"WIPAmount", type number}, {"DiscountAmount", type number}}'
            ),
            "columns": [
                ("BillingEventKey", "int64"), ("DateKey", "int64"), ("MatterKey", "int64"),
                ("ClientKey", "int64"), ("OfficeKey", "int64"), ("PracticeKey", "int64"),
                ("BilledHours", "double"), ("FeeAmount", "double"), ("CostAmount", "double"),
                ("BillingAmount", "double"), ("CashCollected", "double"),
                ("AROutstanding", "double"), ("WIPAmount", "double"), ("DiscountAmount", "double"),
            ],
        },
        "fact_time_entries": {
            "file": data_dir / "fact_time_entries.csv",
            "types": (
                '{{"TimeEntryKey", Int64.Type}, {"DateKey", Int64.Type}, '
                '{"AttorneyKey", Int64.Type}, {"MatterKey", Int64.Type}, '
                '{"OfficeKey", Int64.Type}, {"PracticeKey", Int64.Type}, '
                '{"WorkType", type text}, {"Hours", type number}, '
                '{"StandardRate", Int64.Type}, {"NarrativeQualityScore", Int64.Type}}'
            ),
            "columns": [
                ("TimeEntryKey", "int64"), ("DateKey", "int64"), ("AttorneyKey", "int64"),
                ("MatterKey", "int64"), ("OfficeKey", "int64"), ("PracticeKey", "int64"),
                ("WorkType", "string"), ("Hours", "double"), ("StandardRate", "int64"),
                ("NarrativeQualityScore", "int64"),
            ],
        },
        "fact_legacy_report_inventory": {
            "file": data_dir / "fact_legacy_report_inventory.csv",
            "types": (
                '{{"LegacyReportKey", Int64.Type}, {"LegacyReportName", type text}, '
                '{"LegacyPlatform", type text}, {"OwningStakeholderGroup", type text}, '
                '{"OwningOfficeKey", Int64.Type}, {"OwningPracticeKey", Int64.Type}, '
                '{"Complexity", type text}, {"MigrationStatus", type text}, '
                '{"ValidationStatus", type text}, {"EstimatedHoursRemaining", Int64.Type}, '
                '{"UsageScore", Int64.Type}, {"TargetWorkspace", type text}, '
                '{"ReplacementReportName", type text}}'
            ),
            "columns": [
                ("LegacyReportKey", "int64"), ("LegacyReportName", "string"),
                ("LegacyPlatform", "string"), ("OwningStakeholderGroup", "string"),
                ("OwningOfficeKey", "int64"), ("OwningPracticeKey", "int64"),
                ("Complexity", "string"), ("MigrationStatus", "string"),
                ("ValidationStatus", "string"), ("EstimatedHoursRemaining", "int64"),
                ("UsageScore", "int64"), ("TargetWorkspace", "string"),
                ("ReplacementReportName", "string"),
            ],
        },
        "fact_requirements_backlog": {
            "file": data_dir / "fact_requirements_backlog.csv",
            "types": (
                '{{"RequirementKey", Int64.Type}, {"RequestTitle", type text}, '
                '{"ProductManager", type text}, {"EpicId", type text}, '
                '{"StakeholderGroup", type text}, {"OfficeKey", Int64.Type}, '
                '{"PracticeKey", Int64.Type}, {"KPIArea", type text}, '
                '{"Priority", type text}, {"RequestStatus", type text}, '
                '{"CreatedDate", type date}, {"TargetDate", type date}, '
                '{"SLABreachFlag", Int64.Type}, {"AcceptanceCriteria", type text}}'
            ),
            "columns": [
                ("RequirementKey", "int64"), ("RequestTitle", "string"),
                ("ProductManager", "string"), ("EpicId", "string"),
                ("StakeholderGroup", "string"), ("OfficeKey", "int64"),
                ("PracticeKey", "int64"), ("KPIArea", "string"), ("Priority", "string"),
                ("RequestStatus", "string"), ("CreatedDate", "dateTime"),
                ("TargetDate", "dateTime"), ("SLABreachFlag", "int64"),
                ("AcceptanceCriteria", "string"),
            ],
        },
        "fact_refresh_log": {
            "file": data_dir / "fact_refresh_log.csv",
            "types": (
                '{{"RefreshLogKey", Int64.Type}, {"DateKey", Int64.Type}, '
                '{"DatasetName", type text}, {"RefreshStatus", type text}, '
                '{"DurationMinutes", type number}, {"RowsProcessed", Int64.Type}, '
                '{"FailureCategory", type text}}'
            ),
            "columns": [
                ("RefreshLogKey", "int64"), ("DateKey", "int64"), ("DatasetName", "string"),
                ("RefreshStatus", "string"), ("DurationMinutes", "double"),
                ("RowsProcessed", "int64"), ("FailureCategory", "string"),
            ],
        },
    }


# ---------------------------------------------------------------------------
# semantic model (TMSL / model.bim) construction
# ---------------------------------------------------------------------------

CURRENCY_FMT = '"$"#,0;-"$"#,0;"$"#,0'
PERCENT_FMT = "0.0%;-0.0%;0.0%"
INT_FMT = "#,0"
SCORE_FMT = "0.0"

# Measures: (name, expression, formatString, displayFolder, description?)
MEASURE_DEFINITIONS: List[Tuple[str, str, str, str, str]] = [
    # Financial
    ("Total Billings",   "SUM ( fact_billings[BillingAmount] )",  CURRENCY_FMT, "Financial", "Billings invoiced to clients."),
    ("Total Fees",       "SUM ( fact_billings[FeeAmount] )",      CURRENCY_FMT, "Financial", "Professional fees recognized."),
    ("Total Costs",      "SUM ( fact_billings[CostAmount] )",     CURRENCY_FMT, "Financial", "Direct cost of delivering matters."),
    ("Gross Margin",     "[Total Fees] - [Total Costs]",          CURRENCY_FMT, "Financial", "Fees minus direct costs."),
    ("Gross Margin %",   "DIVIDE ( [Gross Margin], [Total Fees] )", PERCENT_FMT, "Financial", "Gross Margin / Total Fees."),
    ("Cash Collected",   "SUM ( fact_billings[CashCollected] )",  CURRENCY_FMT, "Financial", "Cash receipts against billed amounts."),
    ("Collection Rate",  "DIVIDE ( [Cash Collected], [Total Billings] )", PERCENT_FMT, "Financial", "Cash Collected / Total Billings."),
    ("AR Outstanding",   "SUM ( fact_billings[AROutstanding] )",  CURRENCY_FMT, "Financial", "Accounts receivable balance."),
    ("WIP Amount",       "SUM ( fact_billings[WIPAmount] )",      CURRENCY_FMT, "Financial", "Work in process not yet billed."),
    # Productivity
    ("Billed Hours",     "SUM ( fact_billings[BilledHours] )",    INT_FMT, "Productivity", "Hours billed to clients."),
    ("Total Hours",      "SUM ( fact_time_entries[Hours] )",      INT_FMT, "Productivity", "All recorded hours regardless of work type."),
    ("Billable Hours",   "CALCULATE ( SUM ( fact_time_entries[Hours] ), fact_time_entries[WorkType] = \"Billable\" )", INT_FMT, "Productivity", "Recorded hours flagged Billable."),
    ("Nonbillable Hours","CALCULATE ( SUM ( fact_time_entries[Hours] ), fact_time_entries[WorkType] <> \"Billable\" )", INT_FMT, "Productivity", "Recorded hours other than Billable."),
    ("Billable %",       "DIVIDE ( [Billable Hours], [Total Hours] )", PERCENT_FMT, "Productivity", "Billable / Total recorded hours."),
    ("Realization Rate", "DIVIDE ( [Billed Hours], [Billable Hours] )", PERCENT_FMT, "Productivity", "Billed Hours / Billable Hours - rate at which billable work converts to billed."),
    ("Average Bill Rate","DIVIDE ( [Total Fees], [Billed Hours] )", CURRENCY_FMT, "Productivity", "Effective hourly rate."),
    ("Active Matters",   "DISTINCTCOUNT ( dim_matter[MatterKey] )", INT_FMT, "Productivity", "Distinct matters in current filter."),
    (
        "Open Matters",
        (
            "CALCULATE ( DISTINCTCOUNT ( dim_matter[MatterKey] ), "
            "dim_matter[MatterStatus] <> \"Closed\" )"
        ),
        INT_FMT,
        "Productivity",
        "Distinct matters that are Open or On Hold (non-closed pipeline).",
    ),
    (
        "On Hold Matters",
        (
            "CALCULATE ( DISTINCTCOUNT ( dim_matter[MatterKey] ), "
            "dim_matter[MatterStatus] = \"On Hold\" )"
        ),
        INT_FMT,
        "Productivity",
        "Matters explicitly flagged On Hold.",
    ),
    ("Active Clients",   "DISTINCTCOUNT ( dim_client[ClientKey] )", INT_FMT, "Productivity", "Distinct clients in current filter."),
    # Migration
    ("Legacy Reports",        "COUNTROWS ( fact_legacy_report_inventory )", INT_FMT, "Migration", "Total legacy reports tracked."),
    ("Reports Migrated",      "CALCULATE ( COUNTROWS ( fact_legacy_report_inventory ), fact_legacy_report_inventory[MigrationStatus] = \"Migrated\" )", INT_FMT, "Migration", "Legacy reports moved to Power BI."),
    ("Reports Validated",     "CALCULATE ( COUNTROWS ( fact_legacy_report_inventory ), fact_legacy_report_inventory[ValidationStatus] = \"Validated\" )", INT_FMT, "Migration", "Legacy reports parallel-validated."),
    ("Migration % Complete",  "DIVIDE ( [Reports Migrated], [Legacy Reports] )", PERCENT_FMT, "Migration", "Reports Migrated / Legacy Reports."),
    ("Validation % Complete", "DIVIDE ( [Reports Validated], [Legacy Reports] )", PERCENT_FMT, "Migration", "Reports Validated / Legacy Reports."),
    ("High Complexity Legacy Reports", "CALCULATE ( COUNTROWS ( fact_legacy_report_inventory ), fact_legacy_report_inventory[Complexity] = \"High\" )", INT_FMT, "Migration", "Remaining high-complexity migration items."),
    # Operations / Stakeholders
    ("Open Stakeholder Requests",      "CALCULATE ( COUNTROWS ( fact_requirements_backlog ), fact_requirements_backlog[RequestStatus] IN { \"New\", \"In Discovery\", \"In Build\", \"Blocked\" } )", INT_FMT, "Operations", "Active KPI / dashboard requests in flight."),
    ("Completed Stakeholder Requests", "CALCULATE ( COUNTROWS ( fact_requirements_backlog ), fact_requirements_backlog[RequestStatus] = \"Complete\" )", INT_FMT, "Operations", "Closed / delivered requests."),
    ("SLA Breach Count",               "CALCULATE ( COUNTROWS ( fact_requirements_backlog ), fact_requirements_backlog[SLABreachFlag] = 1 )", INT_FMT, "Operations", "Open requests past target date."),
    # Quality
    ("Refresh Events",            "COUNTROWS ( fact_refresh_log )", INT_FMT, "Quality", "Total refresh attempts logged."),
    ("Successful Refreshes",      "CALCULATE ( COUNTROWS ( fact_refresh_log ), fact_refresh_log[RefreshStatus] = \"Success\" )", INT_FMT, "Quality", "Refreshes completed successfully."),
    ("Failed Refreshes",          "CALCULATE ( COUNTROWS ( fact_refresh_log ), fact_refresh_log[RefreshStatus] = \"Failed\" )", INT_FMT, "Quality", "Refreshes that failed."),
    ("Refresh Success Rate",      "DIVIDE ( [Successful Refreshes], [Refresh Events] )", PERCENT_FMT, "Quality", "Successful / Total refreshes."),
    ("Avg Refresh Duration Minutes", "AVERAGE ( fact_refresh_log[DurationMinutes] )", SCORE_FMT, "Quality", "Average refresh duration in minutes."),
    (
        "As of date",
        (
            "VAR lk = CALCULATE ( MAX ( fact_refresh_log[DateKey] ), REMOVEFILTERS () )\n"
            "RETURN IF (\n"
            "    ISBLANK ( lk ),\n"
            "    BLANK (),\n"
            "    LOOKUPVALUE ( dim_date[Date], dim_date[DateKey], lk )\n"
            ")"
        ),
        "yyyy-MM-dd",
        "Quality",
        "Latest refresh log calendar date (max DateKey → dim_date) for page chrome; use Card visual (text strings error on Card).",
    ),
    # Composite KPI
    ("Modernization Health Score",
     "VAR MigrationScore = [Migration % Complete] * 40\n"
     "VAR ValidationScore = [Validation % Complete] * 30\n"
     "VAR RefreshScore = [Refresh Success Rate] * 30\n"
     "RETURN MigrationScore + ValidationScore + RefreshScore",
     SCORE_FMT, "Composite KPI", "0-100 blended health score: 40% migration progress, 30% validation, 30% refresh reliability."),
]


def make_measure(name: str, expr: str, fmt: str, folder: str, description: str) -> dict:
    measure = {
        "name": name,
        "expression": expr,
        "displayFolder": folder,
        "description": description,
    }
    if fmt:
        measure["formatString"] = fmt
    if fmt == PERCENT_FMT:
        measure["dataType"] = "double"
    if fmt == "yyyy-MM-dd":
        measure["dataType"] = "dateTime"
    return measure


def build_measures_table() -> dict:
    return {
        "name": "_Measures",
        "description": "Centralized measure host. All firmwide KPIs live here; tables remain hidden.",
        "isHidden": False,
        "columns": [
            {
                "name": "_",
                "dataType": "string",
                "isHidden": True,
                "summarizeBy": "none",
                "sourceColumn": "_",
            }
        ],
        "partitions": [
            {
                "name": "_Measures",
                "mode": "import",
                "source": {
                    "type": "calculated",
                    "expression": "ROW(\"_\", BLANK())",
                },
            }
        ],
        "measures": [make_measure(*m) for m in MEASURE_DEFINITIONS],
    }


TIME_INTELLIGENCE_ITEMS: List[Tuple[str, int, str, str]] = [
    ("Current",   0, "SELECTEDMEASURE()", "Current period value (no time shift)."),
    ("MTD",       1, "TOTALMTD ( SELECTEDMEASURE(), dim_date[Date] )", "Month-to-date."),
    ("QTD",       2, "TOTALQTD ( SELECTEDMEASURE(), dim_date[Date] )", "Quarter-to-date."),
    ("YTD",       3, "TOTALYTD ( SELECTEDMEASURE(), dim_date[Date] )", "Year-to-date."),
    ("PY",        4, "CALCULATE ( SELECTEDMEASURE(), SAMEPERIODLASTYEAR ( dim_date[Date] ) )", "Prior year same period."),
    ("PYTD",      5, "CALCULATE ( TOTALYTD ( SELECTEDMEASURE(), dim_date[Date] ), SAMEPERIODLASTYEAR ( dim_date[Date] ) )", "Prior-year YTD."),
    ("YoY",       6,
     "VAR Curr = SELECTEDMEASURE()\n"
     "VAR Prev = CALCULATE ( SELECTEDMEASURE(), SAMEPERIODLASTYEAR ( dim_date[Date] ) )\n"
     "RETURN Curr - Prev",
     "Year-over-year change (current minus prior year)."),
    ("YoY %",     7,
     "VAR Curr = SELECTEDMEASURE()\n"
     "VAR Prev = CALCULATE ( SELECTEDMEASURE(), SAMEPERIODLASTYEAR ( dim_date[Date] ) )\n"
     "RETURN DIVIDE ( Curr - Prev, Prev )",
     "Year-over-year change as a percentage."),
]


def build_calculation_group_table() -> dict:
    return {
        "name": "Time Intelligence",
        "description": "Calculation group for reusable time-intelligence variants on every measure.",
        "calculationGroup": {
            "precedence": 100,
            "calculationItems": [
                {
                    "name": name,
                    "ordinal": ordinal,
                    "expression": expr,
                    "description": description,
                }
                for name, ordinal, expr, description in TIME_INTELLIGENCE_ITEMS
            ],
        },
        "columns": [
            {
                "name": "Time Calculation",
                "dataType": "string",
                "sourceColumn": "Name",
                "summarizeBy": "none",
                "sortByColumn": "Ordinal",
            },
            {
                "name": "Ordinal",
                "dataType": "int64",
                "sourceColumn": "Ordinal",
                "summarizeBy": "none",
                "isHidden": True,
            },
        ],
        "partitions": [
            {
                "name": "Time Intelligence",
                "mode": "import",
                "source": {"type": "calculationGroup"},
            }
        ],
    }


HIERARCHIES = {
    "dim_date": [
        {
            "name": "Calendar",
            "levels": [
                {"name": "Year",    "ordinal": 0, "column": "Year"},
                {"name": "Quarter", "ordinal": 1, "column": "Quarter"},
                {"name": "Month",   "ordinal": 2, "column": "MonthName"},
                {"name": "Date",    "ordinal": 3, "column": "Date"},
            ],
        },
        {
            "name": "Fiscal",
            "levels": [
                {"name": "Fiscal Year",    "ordinal": 0, "column": "FiscalYear"},
                {"name": "Fiscal Quarter", "ordinal": 1, "column": "FiscalQuarter"},
                {"name": "Fiscal Month",   "ordinal": 2, "column": "FiscalMonth"},
                {"name": "Date",           "ordinal": 3, "column": "Date"},
            ],
        },
    ],
    "dim_office": [
        {
            "name": "Geography",
            "levels": [
                {"name": "Region",  "ordinal": 0, "column": "Region"},
                {"name": "Country", "ordinal": 1, "column": "Country"},
                {"name": "Office",  "ordinal": 2, "column": "OfficeName"},
            ],
        }
    ],
    "dim_practice": [
        {
            "name": "Practice",
            "levels": [
                {"name": "Practice Group", "ordinal": 0, "column": "PracticeGroup"},
                {"name": "Practice",       "ordinal": 1, "column": "PracticeName"},
            ],
        }
    ],
}


def make_table(name: str, spec: Dict) -> dict:
    cols = []
    summarize_none_cols = {"Year", "MonthNumber", "FiscalYear", "FiscalMonth",
                            "IsMonthEnd", "IsWeekend", "IsHoliday", "IsActive",
                            "SLABreachFlag", "NarrativeQualityScore"}
    for col, dtype in spec["columns"]:
        c = {"name": col, "dataType": dtype, "sourceColumn": col}
        if col.endswith("Key") or col in summarize_none_cols:
            c["summarizeBy"] = "none"
        cols.append(c)

    table = {
        "name": name,
        "columns": cols,
        "partitions": [
            {
                "name": name,
                "mode": "import",
                "source": {
                    "type": "m",
                    "expression": m_table_expression(name, spec["file"], spec["types"]),
                },
            }
        ],
        "annotations": [{"name": "PBI_ResultType", "value": "Table"}],
    }
    if spec.get("is_date_table"):
        table["dataCategory"] = "Time"
    if name in HIERARCHIES:
        table["hierarchies"] = HIERARCHIES[name]
    return table


def build_relationships() -> List[dict]:
    rels = [
        ("r_bill_date",     "fact_billings",                 "DateKey",         "dim_date",     "DateKey"),
        ("r_bill_matter",   "fact_billings",                 "MatterKey",       "dim_matter",   "MatterKey"),
        ("r_bill_client",   "fact_billings",                 "ClientKey",       "dim_client",   "ClientKey"),
        ("r_bill_office",   "fact_billings",                 "OfficeKey",       "dim_office",   "OfficeKey"),
        ("r_bill_practice", "fact_billings",                 "PracticeKey",     "dim_practice", "PracticeKey"),
        ("r_time_date",     "fact_time_entries",             "DateKey",         "dim_date",     "DateKey"),
        ("r_time_matter",   "fact_time_entries",             "MatterKey",       "dim_matter",   "MatterKey"),
        ("r_time_attorney", "fact_time_entries",             "AttorneyKey",     "dim_attorney", "AttorneyKey"),
        ("r_time_office",   "fact_time_entries",             "OfficeKey",       "dim_office",   "OfficeKey"),
        ("r_time_practice", "fact_time_entries",             "PracticeKey",     "dim_practice", "PracticeKey"),
        ("r_legacy_office",   "fact_legacy_report_inventory", "OwningOfficeKey",   "dim_office",   "OfficeKey"),
        ("r_legacy_practice", "fact_legacy_report_inventory", "OwningPracticeKey", "dim_practice", "PracticeKey"),
        ("r_req_office",    "fact_requirements_backlog",     "OfficeKey",       "dim_office",   "OfficeKey"),
        ("r_req_practice",  "fact_requirements_backlog",     "PracticeKey",     "dim_practice", "PracticeKey"),
        ("r_refresh_date",  "fact_refresh_log",              "DateKey",         "dim_date",     "DateKey"),
        # Intentionally no dim_attorney -> dim_office / dim_practice: fact_time_entries
        # already has OfficeKey and PracticeKey; snowflake edges would duplicate paths
        # (e.g. fact_time_entries -> dim_office vs fact_time_entries -> dim_attorney -> dim_office).
        # Intentionally no dim_matter -> dim_client / dim_office / dim_practice: those edges would
        # duplicate fact_billings paths to dim_client / dim_office and Desktop rejects the model.
    ]
    return [
        {
            "name": n,
            "fromTable": ft,
            "fromColumn": fc,
            "toTable": tt,
            "toColumn": tc,
            "crossFilteringBehavior": "oneDirection",
        }
        for n, ft, fc, tt, tc in rels
    ]


def build_model_bim(table_specs: Dict[str, Dict], data_dir: Path) -> dict:
    expressions = []
    for name, default, ptype in _M_PARAMETERS:
        value = safe_abs(data_dir) if name == "pCsvRoot" else default
        expressions.append({
            "name": name,
            "kind": "m",
            "expression": m_parameter_expression(value, ptype),
            "annotations": [
                {"name": "PBI_NavigationStepName", "value": "Navigation"},
                {"name": "PBI_ResultType", "value": ptype},
            ],
        })

    tables = [make_table(name, spec) for name, spec in table_specs.items()]
    tables.append(build_measures_table())
    tables.append(build_calculation_group_table())

    return {
        "name": PROJECT_NAME,
        "compatibilityLevel": 1567,
        "model": {
            "culture": "en-US",
            # Required by Power BI Desktop when calculation groups exist (Apr 2026+).
            "discourageImplicitMeasures": True,
            "dataAccessOptions": {
                "legacyRedirects": True,
                "returnErrorValuesAsNull": True,
            },
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "en-US",
            "expressions": expressions,
            "tables": tables,
            "relationships": build_relationships(),
            "roles": [
                {
                    "name": "Chicago Office Demo",
                    "description": "RLS Demo page: View as → restricts dim_office to Chicago (OfficeKey 1).",
                    "modelPermission": "read",
                    "tablePermissions": [
                        {
                            "name": "dim_office",
                            "filterExpression": "[OfficeName] = \"Chicago\"",
                        }
                    ],
                },
                {
                    "name": "OfficeKey One (DAX sample)",
                    "description": "Same Chicago slice using OfficeKey (OfficeKey = 1). Compare with Chicago Office Demo.",
                    "modelPermission": "read",
                    "tablePermissions": [
                        {
                            "name": "dim_office",
                            "filterExpression": "[OfficeKey] = 1",
                        }
                    ],
                },
                {
                    "name": "Finance Stakeholder",
                    "modelPermission": "read",
                    "tablePermissions": [
                        {
                            "name": "fact_requirements_backlog",
                            "filterExpression": "[StakeholderGroup] = \"Finance\"",
                        }
                    ],
                },
            ],
            "annotations": [
                {"name": "PBIDesktopVersion", "value": "Generated scaffold"},
                {"name": "DemoContext", "value": "Sidley Austin Senior BI Engineer interview"},
                {"name": "ModelGeneratedAt", "value": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
            ],
        },
    }


# ---------------------------------------------------------------------------
# data quality validation
# ---------------------------------------------------------------------------

@dataclass
class QualityCheck:
    name: str
    passed: bool
    detail: str


def validate_data(data: Dict[str, List[dict]], opts: GeneratorOptions) -> List[QualityCheck]:
    checks: List[QualityCheck] = []

    # row counts
    for tbl, rows in data.items():
        checks.append(QualityCheck(
            name=f"row_count[{tbl}]",
            passed=len(rows) > 0,
            detail=f"{len(rows):,} rows",
        ))

    # date coverage
    expected_days = (opts.end - opts.start).days + 1
    checks.append(QualityCheck(
        name="dim_date.coverage",
        passed=len(data["dim_date"]) == expected_days,
        detail=f"{len(data['dim_date'])} rows for {expected_days} expected days",
    ))

    # foreign key integrity (fact -> dim)
    fk_checks = [
        ("fact_billings",     "DateKey",         "dim_date",     "DateKey"),
        ("fact_billings",     "MatterKey",       "dim_matter",   "MatterKey"),
        ("fact_billings",     "ClientKey",       "dim_client",   "ClientKey"),
        ("fact_billings",     "OfficeKey",       "dim_office",   "OfficeKey"),
        ("fact_billings",     "PracticeKey",     "dim_practice", "PracticeKey"),
        ("fact_time_entries", "DateKey",         "dim_date",     "DateKey"),
        ("fact_time_entries", "MatterKey",       "dim_matter",   "MatterKey"),
        ("fact_time_entries", "AttorneyKey",     "dim_attorney", "AttorneyKey"),
        ("fact_time_entries", "OfficeKey",       "dim_office",   "OfficeKey"),
        ("fact_time_entries", "PracticeKey",     "dim_practice", "PracticeKey"),
        ("fact_legacy_report_inventory", "OwningOfficeKey",   "dim_office",   "OfficeKey"),
        ("fact_legacy_report_inventory", "OwningPracticeKey", "dim_practice", "PracticeKey"),
        ("fact_requirements_backlog",    "OfficeKey",   "dim_office",   "OfficeKey"),
        ("fact_requirements_backlog",    "PracticeKey", "dim_practice", "PracticeKey"),
        ("fact_refresh_log", "DateKey", "dim_date", "DateKey"),
        # dim_matter keys must still resolve to dims (no model relationship; data QA only)
        ("dim_matter", "ClientKey",   "dim_client",   "ClientKey"),
        ("dim_matter", "OfficeKey",   "dim_office",   "OfficeKey"),
        ("dim_matter", "PracticeKey", "dim_practice", "PracticeKey"),
        ("dim_attorney", "OfficeKey",   "dim_office",   "OfficeKey"),
        ("dim_attorney", "PracticeKey", "dim_practice", "PracticeKey"),
    ]
    for fact, fk, dim, pk in fk_checks:
        dim_keys = {row[pk] for row in data[dim]}
        orphans = sum(1 for row in data[fact] if row[fk] not in dim_keys)
        checks.append(QualityCheck(
            name=f"fk_integrity[{fact}.{fk} -> {dim}.{pk}]",
            passed=orphans == 0,
            detail=f"{orphans} orphan(s)",
        ))

    # primary key uniqueness
    pk_specs = [
        ("dim_date",     "DateKey"),
        ("dim_office",   "OfficeKey"),
        ("dim_practice", "PracticeKey"),
        ("dim_client",   "ClientKey"),
        ("dim_attorney", "AttorneyKey"),
        ("dim_matter",   "MatterKey"),
    ]
    for tbl, pk in pk_specs:
        cnt = Counter(row[pk] for row in data[tbl])
        dupes = sum(1 for v in cnt.values() if v > 1)
        checks.append(QualityCheck(
            name=f"pk_unique[{tbl}.{pk}]",
            passed=dupes == 0,
            detail=f"{dupes} duplicate(s)",
        ))

    return checks


def write_quality_report(path: Path, checks: List[QualityCheck], opts: GeneratorOptions) -> bool:
    lines = [
        "# Data Quality Report",
        "",
        f"- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- Seed: {opts.seed}",
        f"- Date range: {opts.start.isoformat()} -> {opts.end.isoformat()}",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    all_passed = True
    for c in checks:
        status = "PASS" if c.passed else "FAIL"
        if not c.passed:
            all_passed = False
        lines.append(f"| {c.name} | {status} | {c.detail} |")
    if all_passed:
        lines.extend(["", "All checks passed."])
    else:
        lines.extend(["", "**One or more checks failed.** Re-generate or inspect upstream sources."])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return all_passed


# ---------------------------------------------------------------------------
# PBIP / report scaffold (unchanged structure, kept stable for Power BI Desktop)
# ---------------------------------------------------------------------------

PAGE_NAMES = [
    ("Executive_Overview",   "Executive Overview"),
    ("Matter_Profitability", "Matter & Practice Profitability"),
    ("Open_Pending_Cases",   "Open & pending cases"),
    ("Legacy_Migration",     "Legacy Report Migration Control Tower"),
    ("Stakeholder_KPIs",     "Stakeholder Requirements / KPI Catalog"),
    ("Refresh_Monitor",      "Data Quality & Refresh Monitor"),
    ("RLS_Demo",             "RLS / Office Security Demo"),
    ("Visual_Lab",           "Visual lab & motion"),
]


def write_registered_theme(report_dir: Path) -> None:
    """Copy custom report theme (sidley.com palette) next to definition/."""
    src = REPORT_ASSETS_DIR / CUSTOM_THEME_FILE
    if not src.is_file():
        raise FileNotFoundError(f"Missing theme asset: {src}")
    dest_dir = report_dir / "StaticResources" / "RegisteredResources"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / CUSTOM_THEME_FILE)


def write_report_platform(report_dir: Path) -> None:
    """Fabric platform file — present on working PBIP exports (e.g. SupplyChain-PBI)."""
    json_dump(report_dir / ".platform", {
        "$schema": (
            "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/"
            "platformProperties/2.0.0/schema.json"
        ),
        "metadata": {"type": "Report", "displayName": PROJECT_NAME},
        "config": {
            "version": "2.0",
            "logicalId": str(uuid.uuid5(uuid.NAMESPACE_URL, f"pbi:///{PROJECT_NAME}.Report")),
        },
    })


def write_semantic_model_platform(model_dir: Path) -> None:
    json_dump(model_dir / ".platform", {
        "$schema": (
            "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/"
            "platformProperties/2.0.0/schema.json"
        ),
        "metadata": {"type": "SemanticModel", "displayName": PROJECT_NAME},
        "config": {
            "version": "2.0",
            "logicalId": str(uuid.uuid5(uuid.NAMESPACE_URL, f"pbi:///{PROJECT_NAME}.SemanticModel")),
        },
    })


def write_report_scaffold(out: Path, report_dir: Path) -> None:
    json_dump(out / f"{PROJECT_NAME}.pbip", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [
            {"report": {"path": f"{PROJECT_NAME}.Report"}}
        ],
        "settings": {"enableAutoRecovery": True},
    })
    (out / ".gitignore").write_text(
        "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n",
        encoding="utf-8",
    )

    json_dump(report_dir / "definition.pbir", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{PROJECT_NAME}.SemanticModel"}},
    })
    write_report_platform(report_dir)
    write_registered_theme(report_dir)

    json_dump(report_dir / "definition" / "version.json", {
        "$schema": (
            "https://developer.microsoft.com/json-schemas/fabric/item/report/"
            "definition/versionMetadata/1.0.0/schema.json"
        ),
        "version": "2.0.0",
    })
    json_dump(report_dir / "definition" / "report.json", {
        "$schema": (
            "https://developer.microsoft.com/json-schemas/fabric/item/report/"
            "definition/report/1.3.0/schema.json"
        ),
        "themeCollection": {
            "baseTheme": {
                "name": "CY24SU10",
                "reportVersionAtImport": THEME_IMPORT_VERSIONS,
                "type": "SharedResources",
            },
            "customTheme": {
                "name": CUSTOM_THEME_DISPLAY_NAME,
                "reportVersionAtImport": THEME_IMPORT_VERSIONS,
                "type": "RegisteredResources",
            },
        },
        "layoutOptimization": "None",
        "resourcePackages": [
            {
                "name": "SharedResources",
                "type": "SharedResources",
                "items": [
                    {
                        "name": "CY24SU10",
                        "path": "BaseThemes/CY24SU10.json",
                        "type": "BaseTheme",
                    }
                ],
            },
            {
                "name": "RegisteredResources",
                "type": "RegisteredResources",
                "items": [
                    {
                        "name": CUSTOM_THEME_DISPLAY_NAME,
                        "path": CUSTOM_THEME_FILE,
                        "type": "CustomTheme",
                    }
                ],
            },
        ],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True,
        },
        "annotations": [
            {"name": "demoPurpose", "value": "Sidley Austin BI modernization interview demo"},
            {
                "name": "candidatePackage",
                "value": (
                    "8-page PBIR report + import semantic model (star schema, DAX in _Measures, "
                    "Time Intelligence calc group, RLS sample roles). Regenerate: py scripts\\\\generate_sidley_pbip.py "
                    "(optional --interview for smaller PBIX). Recruiter PBIX steps: docs/RECRUITER_HANDOFF.md"
                ),
            },
        ],
    })
    page_order = [page_folder_id(emitter) for emitter, _ in PAGE_NAMES]
    landing = page_folder_id(DEFAULT_LANDING_PAGE_KEY)
    if landing not in page_order:
        raise ValueError(f"DEFAULT_LANDING_PAGE_KEY {DEFAULT_LANDING_PAGE_KEY!r} not in PAGE_NAMES")
    json_dump(report_dir / "definition" / "pages" / "pages.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "activePageName": landing,
        "pageOrder": page_order,
    })
    for emitter_key, display in PAGE_NAMES:
        pid = page_folder_id(emitter_key)
        page_obj = {
            "$schema": (
                "https://developer.microsoft.com/json-schemas/fabric/item/report/"
                "definition/page/1.4.0/schema.json"
            ),
            "name": pid,
            "displayName": display,
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280,
        }
        json_dump(report_dir / "definition" / "pages" / pid / "page.json", page_obj)

    emit_all_page_visuals(report_dir / "definition", PAGE_NAMES)


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="generate_sidley_pbip",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--out", type=Path, default=None,
                   help="Output root (default: <package>/output).")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed for deterministic regeneration.")
    p.add_argument(
        "--rows",
        type=int,
        default=None,
        metavar="N",
        help=(
            f"Time-entry row count for fact_time_entries (overrides --interview). "
            f"Default: {DEFAULT_TIME_ENTRY_ROWS}, or {INTERVIEW_TIME_ENTRY_ROWS} when --interview is set."
        ),
    )
    p.add_argument(
        "--interview",
        action="store_true",
        help=(
            f"Smaller gold extract ({INTERVIEW_TIME_ENTRY_ROWS} time-entry rows) for a lighter PBIX "
            f"(e.g. email). Use --rows N to pick another size explicitly."
        ),
    )
    p.add_argument("--start", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
                   default=DEFAULT_START, help="Start date YYYY-MM-DD.")
    p.add_argument("--end", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
                   default=DEFAULT_END, help="End date YYYY-MM-DD.")
    p.add_argument("--databricks", action="store_true",
                   help="Run the Databricks pipeline after generation.")
    p.add_argument("--dry-run", action="store_true",
                   help="When combined with --databricks, log SDK/SQL calls without executing.")
    p.add_argument("--catalog", default=None, help="Override Databricks catalog.")
    p.add_argument("--schema",  default=None, help="Override Databricks schema.")
    p.add_argument("--volume",  default=None, help="Override Databricks volume.")
    p.add_argument("--config", type=Path, default=None,
                   help="Optional databricks.config.json (default: scripts/databricks.config.json).")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")
    p.epilog = (
        "Examples:\n"
        "  py scripts\\generate_sidley_pbip.py\n"
        "  py scripts\\generate_sidley_pbip.py --interview\n"
        "  py scripts\\generate_sidley_pbip.py --rows 8000\n"
        "  py scripts\\generate_sidley_pbip.py --interview --rows 3000"
    )
    return p


def main(argv: List[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    configure_logging(args.verbose)
    log = logging.getLogger("generate_sidley_pbip")

    package_root = Path(__file__).resolve().parents[1]
    out_root = args.out or (package_root / "output")
    out = out_root / PROJECT_NAME
    if out.exists():
        shutil.rmtree(out)

    data_dir = out / "data"
    report_dir = out / f"{PROJECT_NAME}.Report"
    model_dir = out / f"{PROJECT_NAME}.SemanticModel"
    docs_out = out / "docs"

    time_rows = args.rows
    if time_rows is None:
        time_rows = INTERVIEW_TIME_ENTRY_ROWS if args.interview else DEFAULT_TIME_ENTRY_ROWS

    opts = GeneratorOptions(
        out_dir=out,
        seed=args.seed,
        time_entry_rows=time_rows,
        start=args.start,
        end=args.end,
    )

    log.info("Generating data (seed=%s, time_entries=%s)", opts.seed, opts.time_entry_rows)
    data = generate_data(opts)

    log.info("Validating data quality")
    checks = validate_data(data, opts)
    quality_ok = write_quality_report(docs_out / "data_quality_report.md", checks, opts)
    failed = [c for c in checks if not c.passed]
    if failed:
        for c in failed:
            log.error("Quality check FAILED: %s (%s)", c.name, c.detail)
        log.error("Aborting due to data quality failures. See data_quality_report.md")
        return 2

    log.info("Writing CSVs")
    for table, rows in data.items():
        write_csv(data_dir / f"{table}.csv", rows, list(rows[0].keys()))

    log.info("Writing PBIP report scaffold")
    write_report_scaffold(out, report_dir)

    log.info("Writing semantic model (model.bim)")
    table_specs = build_table_specs(data_dir)
    json_dump(model_dir / "definition.pbism", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "1.0",
    })
    json_dump(model_dir / "model.bim", build_model_bim(table_specs, data_dir))
    write_semantic_model_platform(model_dir)

    log.info("Writing Databricks artifacts (DDL + notebook)")
    catalog = args.catalog or "sidley_demo"
    schema = args.schema or "gold"
    write_gold_ddl(docs_out / "gold_layer_ddl.sql", table_specs, catalog=catalog, schema=schema)
    write_pyspark_notebook(docs_out / "databricks_notebook.py")

    src_docs = package_root / "docs"
    docs_out.mkdir(parents=True, exist_ok=True)
    for p in src_docs.glob("*"):
        if p.is_file():
            shutil.copy2(p, docs_out / p.name)

    log.info("Generated: %s", out)
    log.info("Open: %s", out / f"{PROJECT_NAME}.pbip")
    log.info("Data quality: %s", "PASS" if quality_ok else "FAIL")

    if args.databricks:
        log.info("Starting Databricks pipeline (dry_run=%s)", args.dry_run)
        cfg_path = args.config or (package_root / "scripts" / "databricks.config.json")
        cfg = load_config(cfg_path)
        if args.catalog:
            cfg.catalog = args.catalog
        if args.schema:
            cfg.schema = args.schema
        if args.volume:
            cfg.volume = args.volume
        try:
            with DatabricksClient(cfg, dry_run=args.dry_run) as client:
                client.run_full_pipeline(
                    data_dir=data_dir,
                    ddl_path=docs_out / "gold_layer_ddl.sql",
                )
        except RuntimeError as exc:
            log.error("%s", exc)
            if not args.dry_run:
                log.error(
                    "Config file checked: %s (copy from databricks.config.json.example if missing)",
                    cfg_path,
                )
                log.error(
                    "Or set: DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID "
                    "before running with --databricks."
                )
            return 3

    print(f"Generated: {out}")
    print(f"Open: {out / (PROJECT_NAME + '.pbip')}")
    print("If Power BI Desktop reports a metadata issue, use the generated CSVs + docs as the build source, then Save As -> PBIP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
