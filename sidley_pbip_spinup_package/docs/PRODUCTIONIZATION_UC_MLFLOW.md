# Productionization - Unity Catalog, asset bundles, and refresh gates

This document explains how the Sidley demo would graduate from a single PBIP + ad-hoc Databricks calls into a **bundle-deployed, UC-governed** lakehouse pipeline that feeds the certified Power BI semantic model.

It complements `DATABRICKS_INTEGRATION.md` (pipeline mechanics) and `DEPLOYMENT.md` (Power BI Dev/Test/Prod) by focusing on the Databricks-side production patterns.

It does **not** assume your tenant already has Unity Catalog, Databricks Asset Bundles, or MLflow Model Registry wired up - each section calls out **what the demo runs today** vs. **production design intent**.

## What this demonstrates

| Concern | Where it shows up | Production note |
| --- | --- | --- |
| Asset bundle | `databricks/asset_bundle/databricks.template.yml` | Parameterize Dev/Test/Prod targets via bundle variables and service principals; rotate tokens via secret scopes. |
| Unity Catalog provisioning | `databricks_client.ensure_catalog_schema_volume()` and `gold_layer_ddl.sql` | Replace `CREATE CATALOG IF NOT EXISTS` with metastore-admin-owned catalogs; grant `USAGE/SELECT` to a BI service principal only. |
| Gold-layer DDL | `docs/gold_layer_ddl.sql` (emitted alongside `model.bim`) | Pair with table comments, `CHECK` constraints, and `OWNER TO` statements managed in source control. |
| Bronze -> silver -> gold ETL | `docs/databricks_notebook.py` | Schedule with Workflows / Jobs; pass run-time parameters (`as_of_date`, `dataset_version_id`). |
| CSV export for PBIP fallback | `EXPORT_CSV_FOR_PBIP` task parameter | Keep CSV export behind a feature flag; remove once the certified semantic model uses Direct Lake / SQL Warehouse. |
| Observability | `fact_refresh_log` + Refresh Monitor page | Wire alerts (Teams / email / PagerDuty) when `Refresh Success Rate` drops below threshold. |
| Governance | `docs/AI_GOVERNANCE.md` | Responsible AI, data classification, and access reviews live with the firm's IT/Risk program. |
| MLflow (future hook) | Not implemented in the demo | Reserved for forward-looking models: matter-fee forecasting, time-entry anomaly detection, propensity-to-engage on `fact_requirements_backlog`. Register as `catalog.schema.model_name` once UC policies allow. |

## Unity Catalog - design intent

In a UC-enabled workspace you would typically:

1. Register **catalog.schema.table** locations for bronze (raw extracts from billing/timekeeping systems), silver (modeled `dim_*` and `fact_*`), and gold (the same tables the PBIP reads).
2. Grant `SELECT` on the gold schema to the **`sidley-bi-prod` service principal** only; reports never read from silver.
3. Use **Unity Catalog volumes** (`/Volumes/<catalog>/<schema>/<volume>/`) as the landing zone for CSV uploads when bootstrapping (the demo defaults to `sidley_demo.gold.landing`).
4. Promote semantic model lineage by exposing the gold tables through a **SQL Warehouse** that the PBIP semantic model consumes via the `pDataSource = "Databricks"` Power Query parameter.

The demo uses **catalog/schema/volume defaults** (`sidley_demo` / `gold` / `landing`) so it can stand up cleanly in any dev workspace; override with `--catalog`, `--schema`, `--volume` on `generate_sidley_pbip.py`.

## Job DAG mental model

```text
ingest_bronze -> build_silver -> build_gold -> export_csv_for_pbip -> refresh_powerbi_dataset
                                              \-> monitoring (fact_refresh_log, FK/PK checks)
```

Failures in `monitoring` should be treated as **release gates** in production:

- FK / PK violations from `data_quality_report.md` block the gold publish.
- Schema drift on any `dim_*` / `fact_*` table fails the run and skips the Power BI refresh.
- Refresh success rate < target triggers an incident and freezes Test -> Prod promotion until cleared.

## MLflow - where it would fit later

The Sidley demo is a **BI modernization** story, not an ML story. The MLflow surface is intentionally empty today, but the productionization shape would be:

- **Parameters**: `as_of_date`, feature list hash, training window.
- **Metrics**: hold-out RMSE / AUC depending on the model (e.g. matter-fee forecast).
- **Artifact**: the trained pipeline plus a model card describing intended use and known limitations.
- **Registry**: `catalog.schema.model_name` with stage transitions gated by the BI lead and Risk.

When that work starts, point the asset bundle's training task at a new notebook under `databricks/02_train_*` and persist runs to the workspace MLflow tracking server.

## Related files

- [`databricks/asset_bundle/README.md`](../databricks/asset_bundle/README.md)
- [`docs/AI_GOVERNANCE.md`](AI_GOVERNANCE.md)
- [`docs/DATABRICKS_INTEGRATION.md`](DATABRICKS_INTEGRATION.md)
- [`docs/DEPLOYMENT.md`](DEPLOYMENT.md)
- [`docs/gold_layer_ddl.sql`](gold_layer_ddl.sql)
- [`docs/databricks_notebook.py`](databricks_notebook.py)
