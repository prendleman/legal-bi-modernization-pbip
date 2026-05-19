# Copy this file to run_databricks_live.ps1, fill in secrets, then run from the package root:
#   .\scripts\run_databricks_live.ps1
#
# Or paste the three $env: lines into your current PowerShell session before:
#   py scripts\generate_legal_bi_pbip.py --databricks

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$env:DATABRICKS_HOST           = "https://adb-xxxxxxxxxxxxxxxx.azuredatabricks.net"
$env:DATABRICKS_TOKEN          = "dapixxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:DATABRICKS_WAREHOUSE_ID   = "xxxxxxxxxxxxxxxx"  # SQL warehouse GUID (not name)

# Optional overrides:
# $env:DATABRICKS_HTTP_PATH      = "/sql/1.0/warehouses/xxxxxxxxxxxxxxxx"
# $env:DATABRICKS_CATALOG       = "sidley_demo"
# $env:DATABRICKS_SCHEMA        = "gold"
# $env:DATABRICKS_VOLUME        = "landing"

py scripts\generate_legal_bi_pbip.py --databricks
