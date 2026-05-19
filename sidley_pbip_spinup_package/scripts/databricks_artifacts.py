"""Emit static Databricks artifacts derived from the demo's table specs.

These files are produced alongside the CSVs so they can be committed to git,
talked through in interviews, and replayed against a real workspace via
`databricks_client.DatabricksClient`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple


# Mapping from the generator's internal type tags to Databricks SQL types.
_DB_TYPE_MAP = {
    "int64": "BIGINT",
    "double": "DOUBLE",
    "string": "STRING",
    "dateTime": "DATE",
}


def _to_db_type(tag: str) -> str:
    if tag not in _DB_TYPE_MAP:
        raise ValueError(f"Unknown column type tag: {tag}")
    return _DB_TYPE_MAP[tag]


TABLE_COMMENTS = {
    "dim_date": "Conformed date dimension (calendar + fiscal attributes).",
    "dim_office": "Office dimension with region/country rollups.",
    "dim_practice": "Practice and practice group dimension.",
    "dim_client": "Client dimension with industry, tier, risk, status.",
    "dim_attorney": "Attorney dimension with level and standard rate.",
    "dim_matter": "Matter dimension with type, status, lead partner; denormalized office/client/industry/lead names for matter-grain visuals.",
    "fact_billings": "Monthly billing events. Grain: matter / month / event.",
    "fact_time_entries": "Time entries. Grain: attorney / matter / day / work type.",
    "fact_legacy_report_inventory": "Legacy report migration tracker (Cognos / SSRS / etc.).",
    "fact_requirements_backlog": "Stakeholder analytics request backlog.",
    "fact_refresh_log": "Dataset refresh observability log.",
}


def write_gold_ddl(
    path: Path,
    table_specs: Dict[str, Dict],
    catalog: str = "sidley_demo",
    schema: str = "gold",
) -> None:
    """Render `CREATE OR REPLACE TABLE ... USING DELTA` for every table.

    Schemas are derived from the same `columns` lists the generator uses for
    `model.bim`, so the gold layer and the semantic model can never drift.
    """
    lines = [
        "-- Sidley BI Modernization - gold layer DDL",
        "-- Auto-generated. Run via the SQL warehouse to provision Delta tables.",
        f"-- Catalog : {catalog}",
        f"-- Schema  : {schema}",
        "",
        f"CREATE CATALOG IF NOT EXISTS `{catalog}` "
        "COMMENT 'Sidley BI modernization demo';",
        f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}` "
        "COMMENT 'Curated gold layer feeding the Power BI semantic model';",
        "",
    ]
    for name, spec in table_specs.items():
        cols: Iterable[Tuple[str, str]] = spec["columns"]
        col_defs = ",\n    ".join(
            f"`{col}` {_to_db_type(tag)}" for col, tag in cols
        )
        comment = TABLE_COMMENTS.get(name, name)
        lines.extend(
            [
                f"CREATE OR REPLACE TABLE `{catalog}`.`{schema}`.`{name}` (",
                f"    {col_defs}",
                ")",
                "USING DELTA",
                f"COMMENT '{comment}'",
                "TBLPROPERTIES (",
                "    'delta.columnMapping.mode' = 'name',",
                "    'delta.minReaderVersion'  = '2',",
                "    'delta.minWriterVersion'  = '5'",
                ");",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


_NOTEBOOK_TEMPLATE = """# Databricks notebook source
# MAGIC %md
# MAGIC # Sidley BI Modernization - Bronze -> Silver -> Gold
# MAGIC
# MAGIC This notebook illustrates the upstream pipeline that *would* produce
# MAGIC the curated gold tables consumed by the Power BI semantic model.
# MAGIC
# MAGIC In the interview demo the same gold tables are also produced from
# MAGIC `generate_sidley_pbip.py --databricks` (CSVs uploaded to a Unity
# MAGIC Catalog volume and registered as Delta tables). This notebook
# MAGIC demonstrates how the equivalent transformation logic is owned by
# MAGIC the data engineering team in production.

# COMMAND ----------
# MAGIC %md
# MAGIC ## Parameters

# COMMAND ----------
dbutils.widgets.text("catalog", "sidley_demo")
dbutils.widgets.text("schema_bronze", "bronze")
dbutils.widgets.text("schema_silver", "silver")
dbutils.widgets.text("schema_gold",   "gold")

CATALOG       = dbutils.widgets.get("catalog")
SCHEMA_BRONZE = dbutils.widgets.get("schema_bronze")
SCHEMA_SILVER = dbutils.widgets.get("schema_silver")
SCHEMA_GOLD   = dbutils.widgets.get("schema_gold")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Bronze: raw landed extracts from source systems
# MAGIC
# MAGIC In production these come from the time-and-billing system, the matter
# MAGIC management system, the report-inventory tracker, the request intake
# MAGIC system, and the platform refresh telemetry. For the demo we read the
# MAGIC same CSVs that `generate_sidley_pbip.py` produces.

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, DoubleType, DateType, LongType

bronze_root = f"/Volumes/{CATALOG}/{SCHEMA_BRONZE}/landing"

raw_billings = (
    spark.read.option("header", True).csv(f"{bronze_root}/fact_billings.csv")
)
raw_time = (
    spark.read.option("header", True).csv(f"{bronze_root}/fact_time_entries.csv")
)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Silver: typed, deduplicated, business-key validated

# COMMAND ----------
silver_billings = (
    raw_billings
    .withColumn("DateKey",        F.col("DateKey").cast(LongType()))
    .withColumn("BilledHours",    F.col("BilledHours").cast(DoubleType()))
    .withColumn("FeeAmount",      F.col("FeeAmount").cast(DoubleType()))
    .withColumn("CostAmount",     F.col("CostAmount").cast(DoubleType()))
    .withColumn("BillingAmount",  F.col("BillingAmount").cast(DoubleType()))
    .withColumn("CashCollected",  F.col("CashCollected").cast(DoubleType()))
    .withColumn("AROutstanding",  F.col("AROutstanding").cast(DoubleType()))
    .withColumn("WIPAmount",      F.col("WIPAmount").cast(DoubleType()))
    .dropDuplicates(["BillingEventKey"])
)

silver_time = (
    raw_time
    .withColumn("DateKey",       F.col("DateKey").cast(LongType()))
    .withColumn("Hours",         F.col("Hours").cast(DoubleType()))
    .withColumn("StandardRate",  F.col("StandardRate").cast(IntegerType()))
    .dropDuplicates(["TimeEntryKey"])
)

(silver_billings.write
 .mode("overwrite").format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA_SILVER}.fact_billings"))
(silver_time.write
 .mode("overwrite").format("delta")
 .saveAsTable(f"{CATALOG}.{SCHEMA_SILVER}.fact_time_entries"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## Gold: BI-ready dimensional model
# MAGIC
# MAGIC The gold layer is the contract between data engineering and the BI
# MAGIC team. Power BI connects to these tables via a certified semantic
# MAGIC model. Logic lives upstream; DAX stays presentation-focused.

# COMMAND ----------
gold_billings = (
    spark.table(f"{CATALOG}.{SCHEMA_SILVER}.fact_billings")
    .withColumn("GrossMargin", F.col("FeeAmount") - F.col("CostAmount"))
)

(gold_billings.write
 .mode("overwrite").format("delta")
 .option("delta.columnMapping.mode", "name")
 .saveAsTable(f"{CATALOG}.{SCHEMA_GOLD}.fact_billings"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## Quality gates
# MAGIC
# MAGIC Production builds add expectations (Delta Live Tables / Lakeflow
# MAGIC Declarative Pipelines) and route failures into an observability
# MAGIC dashboard mirroring the `fact_refresh_log` table the BI team uses.

# COMMAND ----------
expectations = {
    "fact_billings": "BillingAmount IS NOT NULL AND BillingAmount >= 0",
    "fact_time_entries": "Hours IS NOT NULL AND Hours BETWEEN 0 AND 24",
}

for table, predicate in expectations.items():
    bad = spark.sql(
        f"SELECT COUNT(*) AS bad FROM {CATALOG}.{SCHEMA_GOLD}.{table} "
        f"WHERE NOT ({predicate})"
    ).first()["bad"]
    print(f"{table}: {bad} rows failing `{predicate}`")
"""


def write_pyspark_notebook(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_NOTEBOOK_TEMPLATE, encoding="utf-8")
