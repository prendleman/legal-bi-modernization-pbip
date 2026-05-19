# Legal BI Modernization PBIP Demo Kit

> **Synthetic data only.** This demo uses synthetic professional-services / legal-operations data only. It contains **no Sidley, client, matter, financial, or confidential data**. Public Sidley.com attorney names appear in `dim_attorney` for realism only; see [`sidley_pbip_spinup_package/docs/ATTORNEY_NAMES_ATTRIBUTION.md`](sidley_pbip_spinup_package/docs/ATTORNEY_NAMES_ATTRIBUTION.md). Sidley Austin did not commission, sponsor, or review this repo.

Built for a Sidley Austin **Senior Business Intelligence Engineer** interview process. A source-control-friendly Power BI Project (PBIP) demonstrating legal BI modernization on top of a curated Databricks lakehouse.

## Start here

**Full walkthrough lives in the package README**: [`sidley_pbip_spinup_package/README.md`](sidley_pbip_spinup_package/README.md)

It covers the architecture, fast-start commands, JD mapping, deployment story, and every doc listed below.

## What's in the box

| Area | Where to look |
| --- | --- |
| Generator (one-command PBIP regen + UC pipeline) | [`sidley_pbip_spinup_package/scripts/generate_sidley_pbip.py`](sidley_pbip_spinup_package/scripts/generate_sidley_pbip.py) |
| 8-page PBIP report + TMSL semantic model | [`sidley_pbip_spinup_package/output_test/Sidley_BI_Modernization_Demo/`](sidley_pbip_spinup_package/output_test/Sidley_BI_Modernization_Demo) |
| DAX measures, model design, page build plan | [`sidley_pbip_spinup_package/docs/DAX_MEASURES.dax`](sidley_pbip_spinup_package/docs/DAX_MEASURES.dax) · [`MODEL_DESIGN.md`](sidley_pbip_spinup_package/docs/MODEL_DESIGN.md) · [`PAGE_BUILD_PLAN.md`](sidley_pbip_spinup_package/docs/PAGE_BUILD_PLAN.md) |
| Databricks integration (CSV <-> UC SQL Warehouse) | [`sidley_pbip_spinup_package/docs/DATABRICKS_INTEGRATION.md`](sidley_pbip_spinup_package/docs/DATABRICKS_INTEGRATION.md) |
| Productionization (asset bundles, UC, MLflow hook) | [`sidley_pbip_spinup_package/docs/PRODUCTIONIZATION_UC_MLFLOW.md`](sidley_pbip_spinup_package/docs/PRODUCTIONIZATION_UC_MLFLOW.md) |
| Governance (data classification, RLS, certification) | [`sidley_pbip_spinup_package/docs/AI_GOVERNANCE.md`](sidley_pbip_spinup_package/docs/AI_GOVERNANCE.md) |
| Dev/Test/Prod deployment + retirement flow | [`sidley_pbip_spinup_package/docs/DEPLOYMENT.md`](sidley_pbip_spinup_package/docs/DEPLOYMENT.md) |
| JD-to-demo mapping + interview talk track | [`sidley_pbip_spinup_package/docs/JD_TO_DEMO_MAP.md`](sidley_pbip_spinup_package/docs/JD_TO_DEMO_MAP.md) · [`INTERVIEW_TALK_TRACK.md`](sidley_pbip_spinup_package/docs/INTERVIEW_TALK_TRACK.md) |
| Databricks Asset Bundle template | [`sidley_pbip_spinup_package/databricks/asset_bundle/`](sidley_pbip_spinup_package/databricks/asset_bundle) |

## 90-second pitch

> A small but realistic legal/professional-services BI modernization demo. The theme is migration from Cognos/SSRS-style legacy reporting into Power BI on top of a curated Databricks lakehouse. It includes legal-services entities like matters, practices, offices, attorneys, clients, realization, WIP, collections, and a legacy-report migration control tower. The point isn't the visuals - it's the reusable semantic layer, governed measures, time-intelligence calc group, the Databricks gold-layer integration with a Power Query parameter to flip between CSV and Databricks, and the PBIP/source-control workflow that supports a real BI transformation.
