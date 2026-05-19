# Cert prep (JD: PL-300 / DP-600)

Sidley lists **PL-300** (Power BI Data Analyst) or **DP-600** (Fabric Analytics Engineer) as preferred. You do not need both; pick the credential that matches how the firm runs Fabric / deployment.

## PL-300 — align to this repo

| Exam domain | Use in demo |
|-------------|-------------|
| **Prepare the data** | `model.bim` / Power Query `pDataSource` pattern; CSV vs Databricks M expressions in `generate_sidley_pbip.py`. |
| **Model the data** | Star schema in `MODEL_DESIGN.md`; relationships; **discourageImplicitMeasures**; calculation group in `DAX_MEASURES.dax`. |
| **Visualize the data** | PBIR pages: themes (`SidleyCom.json`), tooltips, synced slicers, native chart variety (`Visual lab` page). |
| **Deploy and maintain** | `DEPLOYMENT.md` (pipelines, RLS rollout); `DATABRICKS_INTEGRATION.md` (parameter overrides). |

**Study tip:** Be able to whiteboard **one** backlog row from `fact_requirements_backlog` through to a **measure** and a **visual filter** (same story as exam “ambiguous requirements” items).

## DP-600 — align to this repo

| Exam theme | Use in demo |
|------------|-------------|
| **Lakehouse / warehouse** | `gold_layer_ddl.sql`, `databricks_notebook.py`, Unity Catalog + `COPY INTO` in `databricks_client.py`. |
| **Semantic models in Fabric** | Same measures/DAX concepts; future state is often **TMDL** / git integration — this kit still uses `model.bim` as the generated interchange format. |
| **Governance** | RLS samples, certified semantic model narrative, retirement gating on legacy inventory. |

**Study tip:** Be explicit that **you** own the **thin semantic model + reports** while **platform/DE** owns medallion ingestion — matches the JD (“not a data engineering role”) without sounding like you avoid the lakehouse.

## One interview sentence

> I’m targeting **PL-300** first for depth on semantic modeling and enterprise report patterns; if Sidley standardizes on **Fabric-first** delivery, **DP-600** is the natural add for lakehouse + deployment alignment.
