-- Sample SQL aligned to the Sidley demo gold star schema (Databricks / Hive / Synapse-flavored).
-- Interview tie-in: jd.txt "Strong SQL and data querying" + coordination with DE on curated tables.

-- ---------------------------------------------------------------------------
-- 1) Finance-style roll-up: billings and margin by calendar month (matches line-chart grain)
-- ---------------------------------------------------------------------------
SELECT
  d.MonthYear,
  SUM(b.BillingAmount) AS total_billings,
  SUM(b.FeeAmount) AS total_fees,
  SUM(b.CostAmount) AS total_costs,
  SUM(b.FeeAmount - b.CostAmount) AS gross_margin,
  SUM(b.FeeAmount - b.CostAmount) / NULLIF(SUM(b.FeeAmount), 0) AS gross_margin_pct
FROM fact_billings b
JOIN dim_date d ON b.DateKey = d.DateKey
GROUP BY d.MonthYear, d.Year, d.MonthNumber
ORDER BY d.Year, d.MonthNumber;

-- ---------------------------------------------------------------------------
-- 2) Marketing / BD lens: billings by client industry (dim_client)
-- ---------------------------------------------------------------------------
SELECT
  c.Industry,
  SUM(b.BillingAmount) AS total_billings,
  COUNT(DISTINCT b.ClientKey) AS active_clients
FROM fact_billings b
JOIN dim_client c ON b.ClientKey = c.ClientKey
GROUP BY c.Industry
ORDER BY total_billings DESC;

-- ---------------------------------------------------------------------------
-- 3) Legacy migration portfolio (same grain as Migration Control Tower)
-- ---------------------------------------------------------------------------
SELECT
  MigrationStatus,
  COUNT(*) AS report_count,
  SUM(CASE WHEN Complexity = 'High' THEN 1 ELSE 0 END) AS high_complexity_count
FROM fact_legacy_report_inventory
GROUP BY MigrationStatus
ORDER BY report_count DESC;

-- ---------------------------------------------------------------------------
-- 4) Requirements intake / SLA risk (stakeholder engineering handoff)
-- ---------------------------------------------------------------------------
SELECT
  ProductManager,
  EpicId,
  StakeholderGroup,
  Priority,
  RequestStatus,
  COUNT(*) AS request_count,
  SUM(SLABreachFlag) AS sla_breach_count
FROM fact_requirements_backlog
GROUP BY ProductManager, EpicId, StakeholderGroup, Priority, RequestStatus
ORDER BY ProductManager, EpicId, StakeholderGroup, Priority, RequestStatus;

-- ---------------------------------------------------------------------------
-- 5) Refresh observability (ops / quality story)
-- ---------------------------------------------------------------------------
SELECT
  d.MonthYear,
  SUM(CASE WHEN r.RefreshStatus = 'Success' THEN 1 ELSE 0 END) AS successful_refreshes,
  COUNT(*) AS refresh_events,
  SUM(CASE WHEN r.RefreshStatus = 'Success' THEN 1 ELSE 0 END) / CAST(COUNT(*) AS DOUBLE) AS refresh_success_rate
FROM fact_refresh_log r
JOIN dim_date d ON r.DateKey = d.DateKey
GROUP BY d.MonthYear, d.Year, d.MonthNumber
ORDER BY d.Year, d.MonthNumber;
