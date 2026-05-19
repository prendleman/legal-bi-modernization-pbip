# Interview Talk Track

## 30-second opener

I built a small but realistic Power BI modernization demo for a legal/professional-services environment. The story is migration from Cognos and SSRS into Power BI sitting on top of a Databricks lakehouse. The PBIP semantic model can read from either local CSVs or a Databricks SQL Warehouse via a Power Query parameter, and there's a real `databricks_client` module that provisions Unity Catalog, runs the gold-layer DDL, uploads the CSVs as a volume, and `COPY INTO`s them into Delta tables.

## JD angles (from `jd.txt`)

- **Product managers + business:** I use PMs for prioritization and sequencing; business owners still sign KPI definitions. The backlog table is the shared artifact so engineering sees **acceptance criteria**, not just a chart title.
- **80/20 build vs stakeholder:** The repo is mostly delivery (model + report + automation); the stakeholder slice is the **requirements** fact and Page 4 — in the job, I’d keep that intake lightweight but non‑negotiable.
- **First six months:** Ship governed dashboards (theme + measures + RLS patterns), run migration waves off the inventory table, and stand up refresh observability — all three show up in this demo.
- **Strong SQL:** Walk through `SQL_GOLD_LAYER_SAMPLES.sql` if they go deep on querying the gold layer before it hits Power BI.
- **Certs (PL-300 / DP-600):** See `CERT_PREP.md` for how exam domains line up with this repo; in the room, state status (planned / in progress / earned).

## Why this fits the role

- Power BI first. Not a backend engineering project.
- Stakeholder translation - `fact_requirements_backlog` with **Product manager**, **Epic id**, priority, status, acceptance criteria (PM + engineering handoff story).
- BI modernization - `fact_legacy_report_inventory` + Migration Control Tower + `Modernization Health Score` KPI.
- Legal / professional-services concepts - matters, clients, practices, offices, attorneys, realization, WIP, AR, collections.
- **Attorney labels** — `dim_attorney[AttorneyName]` uses **public** names from Sidley’s published Management / Executive Committee pages (`sidley_public_attorney_names.json` + `ATTORNEY_NAMES_ATTRIBUTION.md`); all **numbers** are still synthetic seed data.
- Databricks integration - real SDK + SQL connector; the same Python that builds `model.bim` also writes the gold-layer DDL, so schema drift is impossible.

## What I would do in production

1. Confirm KPI definitions with Finance, Marketing / BD, and practice leadership.
2. Own the gold contract with data engineering: medallion architecture in Databricks, DDL versioned in git.
3. Build a certified semantic model with governed measures and the time-intelligence calc group.
4. Thin reports per stakeholder audience.
5. Power BI deployment pipelines (Dev / Test / Prod) overriding the `pDataSource` parameter per stage.
6. RLS by office, practice, leadership group; dynamic RLS via an `office_user_map` table for scale.
7. Refresh observability via `fact_refresh_log` and the Refresh Monitor page.
8. Retire legacy Cognos / SSRS only after parallel validation captured in `fact_legacy_report_inventory`.

## Key phrases worth using

> My bias is to keep complicated transformation logic upstream in Databricks, keep the Power BI model clean, and make the report layer extremely polished and understandable for the business.

> Same model, two sources. The Power Query parameter is how the deployment pipeline switches between dev CSVs and prod Databricks gold tables without touching the file.

> I'd rather have one certified semantic model that ten thin reports point at than ten reports each owning their own data plumbing.

## If asked about ambiguity

> I make the ambiguity visible first: business owner, KPI definition, current report, desired decision, grain, filter behavior, acceptance criteria, validation source. Then I iterate quickly while keeping the semantic layer disciplined.

## If asked about Databricks

> I'd expect Databricks to own ingestion, transformations, and curated gold tables. From Power BI I'd connect to certified gold tables or a governed semantic model and keep DAX focused on reusable business calculations and presentation logic. In this demo the same Python dictionary that drives `model.bim` also writes `gold_layer_ddl.sql`, and the `databricks_client` module performs the full `CREATE CATALOG / SCHEMA / VOLUME -> upload -> COPY INTO` flow with a `--dry-run` mode for rehearsal.

## If asked about migration sequencing

> The Migration Control Tower drives retirement, not the other way around. A legacy report is captured with platform, owner, and complexity. The Power BI replacement gets built, parallel-validated for a full reporting cycle, signed off by the stakeholder, and only then is the legacy report flipped to Retired and access removed.
