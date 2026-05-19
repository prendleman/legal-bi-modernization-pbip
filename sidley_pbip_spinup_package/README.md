# Sidley Austin BI Modernization - PBIP Demo Kit

A fast-start, source-control-friendly Power BI Project (PBIP) tailored to the Sidley Austin **Senior Business Intelligence Engineer** role. It demonstrates:

- Power BI specialist depth (semantic model, DAX, calc groups, hierarchies, RLS)
- Enterprise BI modernization from Cognos / SSRS into Power BI
- A real Databricks integration: Unity Catalog gold tables, SQL Warehouse connectivity, and a sample bronze -> silver -> gold notebook
- Stakeholder-facing KPI thinking for Finance, Marketing / BD, and firm leadership
- A production-realistic deployment story (Dev / Test / Prod, certified semantic model, observability)
- Git-friendly PBIP with line-ending normalization and reproducible builds

## Fast start

```powershell
cd sidley_pbip_spinup_package
py scripts\generate_sidley_pbip.py
```

Smaller **`fact_time_entries`** (lighter PBIX for email): add **`--interview`** (4,500 rows) or set an explicit count with **`--rows N`** (overrides `--interview`).

```powershell
py scripts\generate_sidley_pbip.py --interview
```

**CI smoke** (regenerate + parse all output JSON + page count):

```powershell
py scripts\smoke_pbip.py
py scripts\smoke_pbip.py --interview   # regenerate with smaller fact_time_entries, then same JSON checks
```

If your prompt is already `...\sidley_pbip_spinup_package>`, run that command only. A second `cd sidley_pbip_spinup_package` fails because it looks for a nested folder that does not exist. From repo root `...\sid` you can use `python scripts\smoke_pbip.py` instead (see `scripts/smoke_pbip.py` one level above this package).

Use **Power BI Desktop** with **PBIR / developer mode** enabled (preview feature names vary by month; the scaffold targets **report definition 1.3.x / page 1.4.x** and **Fabric `version.json` 2.0.0**). If a build rejects JSON, save once from Desktop and diff the normalized files.

Then open:

```text
output\Sidley_BI_Modernization_Demo\Sidley_BI_Modernization_Demo.pbip
```

### Sharing as PBIX (e.g. with a recruiter)

Open the PBIP in **Power BI Desktop**, let **Refresh** complete, then **File → Save As → `.pbix`**. The PBIX embeds the CSV data; recipients only need Desktop. Copy-ready **email text** and step-by-step notes are in **`docs/RECRUITER_HANDOFF.md`** (also copied into `output/.../docs/` on each generate).

For the Databricks pipeline (no credentials required - prints every SDK / SQL call):

```powershell
py scripts\generate_sidley_pbip.py --databricks --dry-run
```

For a real Databricks workspace:

```powershell
$env:DATABRICKS_HOST  = "https://adb-xxxxx.x.azuredatabricks.net"
$env:DATABRICKS_TOKEN = "dapi..."
$env:DATABRICKS_WAREHOUSE_ID = "abcdef1234567890"
pip install -r requirements.txt
py scripts\generate_sidley_pbip.py --databricks
```

## CLI reference

```text
py scripts\generate_sidley_pbip.py [--out PATH] [--seed N] [--rows N]
                                   [--start YYYY-MM-DD] [--end YYYY-MM-DD]
                                   [--databricks] [--dry-run]
                                   [--catalog NAME] [--schema NAME] [--volume NAME]
                                   [--config PATH] [-v]
```

| Flag | Purpose |
|---|---|
| `--seed` | Deterministic regeneration. |
| `--rows` | Override the default 26,000 time entries. |
| `--start` / `--end` | Calendar range covered by `dim_date` and the data. |
| `--databricks` | Run the UC provisioning + DDL + upload + COPY INTO pipeline. |
| `--dry-run` | Combined with `--databricks`, log every call without executing. |
| `--catalog` / `--schema` / `--volume` | Override Unity Catalog targets. |

## What gets generated

```text
output/Sidley_BI_Modernization_Demo/
  Sidley_BI_Modernization_Demo.pbip
  Sidley_BI_Modernization_Demo.Report/      # PBIR: 8 pages + visuals (see scripts/pbir_visuals.py)
  Sidley_BI_Modernization_Demo.SemanticModel/
    definition.pbism
    model.bim                                # TMSL JSON: tables, relationships,
                                             # measures, calc group, hierarchies,
                                             # Power Query parameters, RLS roles
  data/                                      # 11 curated CSVs (gold layer)
  docs/
    DAX_MEASURES.dax
    MODEL_DESIGN.md                          # Mermaid star schema diagram
    PAGE_BUILD_PLAN.md                       # Per-page build recipe + bookmarks
    BOOKMARKS_AND_NAV.md                     # Bookmarks (Desktop) + optional tooltip notes
    CUSTOM_VISUALS_AND_ANIMATION.md          # Custom visuals workflow + motion (bookmarks / transitions)
    INTERVIEW_TALK_TRACK.md
    ATTORNEY_NAMES_ATTRIBUTION.md            # Why public Sidley.com names appear in synthetic dim_attorney
    JD_TO_DEMO_MAP.md                        # Full jd.txt → demo mapping (interview checklist)
    CERT_PREP.md                             # PL-300 / DP-600 study map tied to this repo
    SQL_GOLD_LAYER_SAMPLES.sql             # Sample joins for SQL depth (JD)
    DEPLOYMENT.md                            # Dev/Test/Prod, RLS, retirement flow
    DATABRICKS_INTEGRATION.md                # Architecture + config + pipeline
    gold_layer_ddl.sql                       # CREATE OR REPLACE TABLE (Delta)
    databricks_notebook.py                   # Bronze -> silver -> gold PySpark
    data_quality_report.md                   # FK / PK / coverage validation
```

## Highlights aimed at the Sidley JD

| JD ask | Demo response |
|---|---|
| Power BI dashboards & reports | 8-page report (six core pages + **Open & pending cases** waterfall + **Visual lab & motion**). |
| Semantic / data models where needed | Star schema + calc group for time intelligence + hierarchies + display folders + format strings. |
| Translate business requirements into specs | `fact_requirements_backlog` with stakeholder, priority, status, target, acceptance criteria. |
| Finance / Marketing / leadership stakeholders | KPIs grouped into Financial / Productivity / Migration / Operations / Quality folders; **Executive** adds **industry** billings mix (`dim_client[Industry]`). |
| Cognos / SSRS migration | `fact_legacy_report_inventory` + Migration Control Tower page + `Modernization Health Score` composite KPI. |
| Databricks exposure (preferred) | Real `databricks_client.py` (SDK + SQL connector), Unity Catalog volume upload, COPY INTO Delta tables, sample bronze->silver->gold notebook, model toggle between CSV and Databricks SQL Warehouse. |
| Polished outputs quickly | One-command generation with deterministic seed; data quality report runs every build. |
| **Strong SQL** (JD) | `docs/SQL_GOLD_LAYER_SAMPLES.sql` — month / industry / migration / backlog / refresh queries on the same gold grain as the model. |
| **PM + business + engineering** (JD) | Backlog rows include **acceptance criteria** and status for handoff; talk track names PM vs business owner vs DE. |
| **~80% build / ~20% stakeholder** (JD) | Repo weighted to delivery artifacts; stakeholder work modeled in **Page 4** + narrative in `JD_TO_DEMO_MAP.md`. |
| **First 6 months success** (JD) | Same doc maps “production-ready dashboards,” stakeholder execution, and migration contribution to concrete pages/measures. |
| **PL-300 / DP-600** (preferred, JD) | `docs/CERT_PREP.md` — how exam domains map to this PBIP + lakehouse artifacts. |

## Two-mode data source

The PBIP semantic model can read from either local CSVs or a Databricks SQL Warehouse - same model, no edits. A Power Query parameter `pDataSource` switches every table:

```text
pDataSource = "CSV"         -> reads data\*.csv (default, runs anywhere)
pDataSource = "Databricks"  -> Databricks.Catalogs(host, httpPath, [Catalog, Database])
```

In production this parameter is overridden per workspace by the deployment pipeline. See `docs/DATABRICKS_INTEGRATION.md`.

## Power BI Desktop note

PBIP / PBIR / TMSL support continues to evolve. This kit uses a source-control-friendly PBIP scaffold and a TMSL semantic model definition. Depending on your Power BI Desktop version, Desktop may normalize files when you open and save.

Open the generated **`output\Sidley_BI_Modernization_Demo\Sidley_BI_Modernization_Demo.pbip`** (or re-run `python scripts\smoke_pbip.py`) so new pages match `scripts/generate_sidley_pbip.py`.

If Desktop rejects a generated report metadata file, fall back to the durable build artifacts:

1. Create a blank Power BI report.
2. Load all CSVs from `data/`.
3. Build relationships from `docs/MODEL_DESIGN.md`.
4. Paste measures from `docs/DAX_MEASURES.dax` (formats and folders documented per measure).
5. Save as PBIP.
6. Build pages per `docs/PAGE_BUILD_PLAN.md`.

That still lets you say honestly that the demo was generated from code and shaped into PBIP for source control.

## Semantic model: `model.bim` vs TMDL (Fabric / Git)

This kit keeps a **single `model.bim`** (TMSL) under `Sidley_BI_Modernization_Demo.SemanticModel/` so the Python generator can regenerate the full model in one step with minimal merge surface for interviews and spin-ups.

Longer term, enterprise Fabric repos often use the **folder model** layout (`definition/` with `.tmdl` fragments per table). That is a **separate migration**: Desktop or Tabular Editor can convert folder model ↔ single `.bim`; this generator does not emit TMDL yet. When you adopt TMDL, treat `model.bim` as the interchange format for scripted regen, then let tooling split into `definition/*.tmdl` for day-to-day Git merges.

## Report polish (generated PBIR)

- **Page chrome:** each page gets title + subtitle, a **Certified extract · data through** caption, and an **As of** card (`_Measures[As of date]`, a **date** measure — classic Card visuals error on text measures).
- **Two-layer time:** a cross-page synced **`dim_date[Date]`** slicer in **Between** mode defines the **calendar window** (what appears on time axes and which fact rows qualify). The **`Time Intelligence[Time Calculation]`** slicer applies **semantics** (Current, MTD, YTD, PY, YoY) on top of that window — it does not replace the date window.
- **Cross-page slicers:** `syncGroup` is emitted with stable names (see `docs/PAGE_BUILD_PLAN.md`); re-diff after any Desktop slicer export before renaming.
- **Executive:** billings line (with **report page tooltip**), margin by practice column, **client billings bar**; **Matter:** fees + **realization** by practice plus **scatter** (fees vs margin %, bubble size WIP); **Legacy:** **donut** + inventory table; **Visual lab:** treemap, donut, funnel, scatter + notes for custom visuals and motion (`docs/CUSTOM_VISUALS_AND_ANIMATION.md`).
- **Bookmarks / nav:** capture in Desktop (see `docs/BOOKMARKS_AND_NAV.md`) — bookmark `explorationState` is not regenerated here.

## RLS sample roles → RLS Demo page

The semantic model includes **Chicago Office Demo** (`dim_office[OfficeName] = "Chicago"`), **OfficeKey One (DAX sample)** (`dim_office[OfficeKey] = 1`), and **Finance Stakeholder** (requirements table). Open the **RLS / office security demo** report page, then **Modeling → View as roles** and toggle between the Chicago roles to show the same office slice via name vs key filter.

## Suggested demo title

**Legal BI Modernization Control Tower: Power BI + Curated Lakehouse Analytics**

## 90-second pitch

> I built a small but realistic legal/professional-services BI modernization demo. The theme is migration from Cognos/SSRS-style legacy reporting into Power BI on top of a curated Databricks lakehouse. It includes legal-services-friendly entities like matters, practices, offices, attorneys, clients, realization, WIP, collections, and a legacy-report migration control tower. The point isn't the visuals - it's the reusable semantic layer, governed measures, time-intelligence calc group, the Databricks gold-layer integration with a Power Query parameter to flip between CSV and Databricks, and the PBIP/source-control workflow that supports a real BI transformation.

## What I would do in production

1. Confirm source-of-truth KPI definitions with Finance, Marketing / BD, and practice leadership.
2. Use Databricks medallion architecture for ingestion, transformations, and curated gold tables (DDL is in `docs/gold_layer_ddl.sql`; the notebook in `docs/databricks_notebook.py` is the production starting point).
3. Build a certified semantic model with governed measures and the time-intelligence calc group.
4. Create thin reports for each major stakeholder audience.
5. Set up Power BI deployment pipelines (Dev / Test / Prod) with the data-source parameter overridden per stage.
6. Add RLS by office, practice, and leadership group; mature to dynamic RLS via an `office_user_map` table.
7. Monitor refresh reliability and adoption via `fact_refresh_log` and the Refresh Monitor page.
8. Retire legacy Cognos / SSRS reports only after parallel validation captured in `fact_legacy_report_inventory`.
