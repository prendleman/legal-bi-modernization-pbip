# Databricks Asset Bundles - Sidley legal-BI pipeline

Template file: **`databricks.template.yml`** (sibling of this README).

Goal: ship the Sidley bronze -> silver -> gold pipeline as a versioned **Databricks Asset Bundle** so Dev / Test / Prod targets are deployed from the same source, with the **same gold contract** the PBIP semantic model already consumes via `pDataSource`.

This complements:

- `docs/DATABRICKS_INTEGRATION.md` (two-mode CSV/Databricks data source + pipeline mechanics)
- `docs/PRODUCTIONIZATION_UC_MLFLOW.md` (UC + asset bundle + refresh gates)
- `docs/DEPLOYMENT.md` (Power BI Dev/Test/Prod promotion)

## Prerequisites

1. **Databricks CLI v0.205+** with bundles: [Install](https://docs.databricks.com/dev-tools/cli/install.html).
2. **Auth**: `databricks auth login` (OAuth) or a token via env - **never commit tokens**.
3. **Workspace URL**, e.g. `https://adb-1234567890.10.azuredatabricks.net`.
4. **Unity Catalog catalog + schema + volume** matching the bundle variables (defaults: `sidley_demo` / `gold` / `landing`). The demo's `--databricks` flag in `generate_sidley_pbip.py` provisions these idempotently.

## One-time setup

```powershell
cd "path\to\sid"

# Copy template to repo root (bundles resolve paths from root).
copy sidley_pbip_spinup_package\databricks\asset_bundle\databricks.template.yml .\databricks.yml

# Optional: edit spark_version / node_type_id for your region quota.
```

Set the workspace host either inside `databricks.yml` under `targets.dev.workspace.host` or via bundle variable override:

```powershell
$env:WORKSPACE_HOST = "https://adb-xxxx.x.azuredatabricks.net"
```

If your CLI expects a profile:

```powershell
$env:DATABRICKS_CONFIG_PROFILE = "DEFAULT"
```

## Notebook layout

The bundle references the bronze -> silver -> gold notebook that ships with the demo:

| Bundle path | Source file |
| --- | --- |
| `./sidley_pbip_spinup_package/docs/databricks_notebook` | `sidley_pbip_spinup_package/docs/databricks_notebook.py` (`# Databricks notebook source` style) |

Two ways to make the path resolvable in the workspace:

- **Repos** (recommended): clone this repo as a Databricks Repo so `/Repos/<you>/sid/sidley_pbip_spinup_package/docs/databricks_notebook` matches the bundle's relative path. The bundle CLI normalizes the prefix.
- **Workspace upload**: change `notebook_task.notebook_path` to `/Workspace/Users/you@firm/sidley_databricks_notebook` after importing.

Validate paths before deploy:

```powershell
databricks bundle validate --target dev
```

## Deploy

```powershell
databricks bundle deploy --target dev
```

Then open **Workflows / Jobs** in the workspace UI and **Run now** on `[demo] Sidley BI - bronze -> silver -> gold`.

The `export_csv_for_pbip` task is what keeps the PBIP demo runnable on a laptop after the lakehouse pipeline has owned the gold contract: it materializes the same CSVs in `data/` that `model.bim` reads under `pDataSource = "CSV"`. Drop the task once the certified semantic model is on the SQL Warehouse path.

## Bundle variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `workspace_host` | `${WORKSPACE_HOST}` | Workspace URL per target. |
| `catalog` | `sidley_demo` | Matches `generate_sidley_pbip.py --catalog`. |
| `schema` | `gold` | Matches `--schema`. |
| `volume` | `landing` | Matches `--volume`; CSV landing zone for `COPY INTO`. |

Override per environment with `--var "catalog=sidley_prod"` etc., or set `bundle.variables.<name>.default` on a per-target basis.

## Option B - Jobs API (alternative to bundles)

`databricks bundle deploy` ultimately persists job definitions through the same **Jobs API** you can call from CI without the bundle YAML. Useful when:

- Your tenant has not yet enabled bundles for service principals.
- You want a single Python script in CI rather than a YAML + CLI step.

Pattern:

```powershell
pip install -r sidley_pbip_spinup_package\requirements.txt
$env:DATABRICKS_HOST = "https://adb-xxxx.x.azuredatabricks.net"
$env:DATABRICKS_TOKEN = "<personal-access-token>"
$env:DATABRICKS_WAREHOUSE_ID = "<sql-warehouse-id>"
py sidley_pbip_spinup_package\scripts\generate_sidley_pbip.py --databricks --dry-run
```

The `--databricks` flag goes through the same UC provisioning + `COPY INTO` steps the bundle's notebook would; `--dry-run` prints every SDK call without executing.

## Common failures

| Symptom | Fix |
| --- | --- |
| `notebook_path` not found | Bundle paths are workspace paths; sync the Databricks Repo or fix the prefix (`/Repos/...`). |
| Spark version unavailable | Pick a supported runtime from workspace **Clusters -> Create -> Runtime** and update `spark_version`. |
| Permission denied | The job runner needs `CAN MANAGE` on the cluster policy / notebook paths, plus `USAGE` on the catalog and `MODIFY` on the schema. |
| Cluster startup quota | Reduce `num_workers` or switch to an instance pool / smaller `node_type_id`. |
| CSV export missing | Ensure `EXPORT_CSV_FOR_PBIP = "true"` on the export task; without it the PBIP's `pDataSource = "CSV"` path will read stale files. |

## Production-shaped next steps (talk track)

- Split **build_gold** and **export_csv_for_pbip** into separate jobs with schedules and dependencies.
- Replace CSV export with **Direct Lake** / **SQL Warehouse** as the certified semantic model's source; toggle `pDataSource = "Databricks"` per the Power BI deployment pipeline.
- Add a **monitoring** task that posts to Teams when `fact_refresh_log` shows degraded success rate.
- Wire **GitHub Actions**: `databricks bundle deploy --target test` only after `smoke_pbip.py` passes; promote to `prod` only after stakeholder sign-off recorded against `fact_requirements_backlog`.
- Move per-target hosts and catalogs into a bundle **variables** file checked into source control alongside this template.
