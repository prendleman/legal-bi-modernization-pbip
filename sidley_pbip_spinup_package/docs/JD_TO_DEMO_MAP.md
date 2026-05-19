# Sidley JD → Demo Mapping

Source: `jd.txt` (Senior Business Intelligence Engineer). This file is the interview checklist: **point to a doc, a script, a page, or a query** for each JD line.

---

## Role shape (Overview / What the role focuses on)

| JD theme | How the demo answers it |
|----------|-------------------------|
| **Front-end BI** (not a DE role) | Report + semantic model are the hero; Databricks artifacts show *coordination* with DE, not owning the whole pipeline. |
| **~80% build / ~20% stakeholder** | Most repo surface is PBIP + model + automation; stakeholder work is represented by **requirements backlog** + **talk track** (`INTERVIEW_TALK_TRACK.md`). Say explicitly in interview: intake is modeled in data so delivery stays measurable. |
| **Partner PMs + business; translate needs into specs engineering can support** | `fact_requirements_backlog`: **Product manager**, **Epic id**, stakeholder, KPI area, priority, status, target date, **acceptance criteria** → spec-shaped rows. **Page 4** makes the backlog visible. Narrative: “this row is what I’d hand to DE for *new* ingestion vs what stays in semantic model DAX.” |
| **Gaps in curated data → coordinate with DE** | `data_quality_report.md` on every build; **Refresh Monitor** page; `DATABRICKS_INTEGRATION.md` describes when to push logic upstream vs add measures. |

---

## Success in the first 6 months (JD)

| JD success criterion | Demo / talking point |
|----------------------|----------------------|
| **Production-ready dashboards** | Themed PBIR, governed measures, RLS sample roles, deployment doc (`DEPLOYMENT.md`), DQ gates on generate. |
| **Partner stakeholders; execute reporting needs** | Backlog table + SLA breach measure + stakeholder groups (Finance, Marketing / BD, Practice Leadership). |
| **Contribute to legacy → Power BI migration** | `fact_legacy_report_inventory` + migration/validation statuses + **Modernization Health Score**. |

---

## Strong hire / Miss (JD)

| JD signal | What to show |
|-----------|----------------|
| **Strong hire**: independent, polished, fast, good with stakeholders | One-command `generate_sidley_pbip.py`, deterministic data, git-friendly PBIP; `INTERVIEW_TALK_TRACK.md` “ambiguity” section. |
| **Miss**: weak Power BI, ambiguity, stakeholder comms | Counter with: calc group, field parameters pattern (time), RLS demo page, requirements spec fields, and a live “how I’d run a KPI definition session” story. |

---

## Environment & data stack (JD)

| JD line | Demo response |
|---------|----------------|
| **Power BI primary** | Full PBIP report: **8 pages** — Executive, Matter, **Open & pending cases** (waterfall), Legacy, Stakeholder, Refresh, RLS, **Visual lab & motion**. |
| **Databricks foundation** | `pDataSource` toggle, `databricks_client.py`, `gold_layer_ddl.sql`, notebook, `DATABRICKS_INTEGRATION.md`. |
| **Logic upstream; viz-focused** | Gold CSVs + DDL as contract; model stays relatively thin; talk track says heavy transform belongs in lakehouse. |

---

## Candidate profile → artifact

| JD requirement | Where it shows up |
|----------------|-------------------|
| **Enterprise BI / Power BI depth** | PBIR layout code (`scripts/pbir_visuals.py`), theme (`SidleyCom.json`), calc group, tooltips, Visual lab native chart types. |
| **Other BI platforms + willingness on Power BI** | Cognos/SSRS **migration** story in data + Legacy page; mention Tableau/Qlik only if asked — same “certified semantic model, thin reports” pattern. |
| **Strong SQL** | **`docs/SQL_GOLD_LAYER_SAMPLES.sql`** — joins aligned to star schema / report grain. |
| **Semantic models, DAX, Power Query, viz best practices** | `model.bim`, `DAX_MEASURES.dax`, PQ parameters in generator, `MODEL_DESIGN.md`, theme + `CUSTOM_VISUALS_AND_ANIMATION.md`. |
| **Stakeholder-facing** | Backlog fact + Page 4 + measure display folders by audience. |
| **Cloud data platform (Databricks preferred)** | Full Databricks path above. |
| **Legal / professional services** | Matters, clients, practices, realization, WIP, AR, collections, industry/tier on `dim_client`. |
| **Modernization / migration** | Legacy inventory + validation + health score. |
| **PL-300 / DP-600 (preferred)** | `docs/CERT_PREP.md` maps exam domains to this PBIP + lakehouse; pair with your own practice tests. |

---

## Semantic / data models (JD)

- **Star schema:** six dimensions (`dim_date`, `dim_office`, `dim_practice`, `dim_client`, `dim_matter`, `dim_attorney`) and five facts (`fact_billings`, `fact_time_entries`, `fact_legacy_report_inventory`, `fact_requirements_backlog`, `fact_refresh_log`). Diagram: `MODEL_DESIGN.md`.
- **Hierarchies:** Calendar + Fiscal on date; Geography on office; Practice on practice.
- **Time intelligence:** calculation group on `Time Intelligence[Time Calculation]` (`Current`, `MTD`, `QTD`, `YTD`, `PY`, `PYTD`, `YoY`, `YoY %`).
- **Measures:** display folders + format strings; see `DAX_MEASURES.dax`.
- **RLS (sample):** **three** roles in `model.bim` — **Chicago Office Demo**, **OfficeKey One (DAX sample)**, **Finance Stakeholder** — see `DEPLOYMENT.md` and RLS demo page.

---

## Dashboards & reports (JD)

- **Core pages:** Executive, Matter, Legacy, Stakeholder, Refresh, RLS — each maps to a JD pillar (firm KPIs, profitability, migration, intake, quality, security).
- **Visual lab:** deliberate “polish + chart literacy” page; optional custom visual merge workflow in `CUSTOM_VISUALS_AND_ANIMATION.md`.
- **Tooltips:** Executive line uses the default tooltip; add an optional report-page tooltip in Desktop if you want a custom canvas (see `BOOKMARKS_AND_NAV.md`).
- **Bookmarks / motion:** not generated as JSON (IDs drift) — capture in Desktop per `BOOKMARKS_AND_NAV.md`.

---

## Gaps you can still **say** without more code

- **Years of experience / BA** — resume, not repo.
- **PL-300 / DP-600** — see `CERT_PREP.md`; certificate status belongs on resume / LinkedIn.
- **Product manager** — name the role explicitly: “I treat PM as prioritization + roadmap; business owners own KPI definitions; I own traceability from ask → measure → visual.”

---

## One-line close for the loop

> This repo is a **thin vertical slice**: same tables in CSV, Delta DDL, and `model.bim`, so nothing drifts — that’s how I’d de-risk delivery with DE while staying **Power BI–first**.
