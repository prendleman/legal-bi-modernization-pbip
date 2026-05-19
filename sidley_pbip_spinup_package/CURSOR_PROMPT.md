# Cursor Prompt: Sidley Austin PBIP Demo

You are helping me build a Power BI PBIP demo for a Senior Business Intelligence Engineer interview at Sidley Austin.

The role is focused on Power BI dashboards, semantic models where needed, stakeholder engagement, KPI definition, and BI modernization from Cognos / SSRS to Power BI over a Databricks-style curated data platform.

## Goal

Turn this starter kit into a polished, interview-ready PBIP project called:

**Legal BI Modernization Control Tower**

## Constraints

- Keep the demo front-end BI focused.
- Do not overbuild backend engineering.
- Use the generated CSVs as curated “gold layer” extracts.
- Improve the model, DAX, page layout, and documentation.
- Keep everything source-control friendly.
- Use enterprise BI naming conventions.
- Prioritize polished output quickly.

## Deliverables

1. A Power BI report (see `docs/JD_TO_DEMO_MAP.md` for JD line-by-line mapping) with **eight** pages:
   - Executive Overview
   - Matter & Practice Profitability
   - Open & pending cases (matter waterfall)
   - Legacy Report Migration Control Tower
   - Stakeholder Requirements / KPI Catalog
   - Data Quality & Refresh Monitor
   - RLS / Office Security Demo
   - Visual lab & motion (native chart variety + custom visual / bookmark notes)

2. A clean semantic model:
   - Dimensions: Date, Office, Practice, Client, Matter, Attorney
   - Facts: Billings, Time Entries, Legacy Report Inventory, Requirements Backlog, Refresh Log

3. Measures:
   - Total Billings
   - Total Fees
   - Total Costs
   - Gross Margin
   - Gross Margin %
   - Billable Hours
   - Nonbillable Hours
   - Realization Rate
   - Collection Rate
   - WIP Amount
   - AR Outstanding
   - Migration % Complete
   - Refresh Success Rate
   - Open Stakeholder Requests
   - SLA Breach Count

4. Interview polish:
   - README + `docs/JD_TO_DEMO_MAP.md` map to `jd.txt`; `docs/SQL_GOLD_LAYER_SAMPLES.sql` supports the “strong SQL” JD line.
   - Add a short talk track.
   - Add visual build notes.
   - Add a “what I would do in production” section covering Databricks, governance, deployment pipelines, RLS, and certified semantic models.

## Style

Executive legal/professional-services dashboard:
- crisp
- conservative
- high signal
- stakeholder ready
- not gimmicky
- polished enough to show to a partner, CFO, CMO, or BI director
