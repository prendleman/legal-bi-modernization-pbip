# Databricks notebook source
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
