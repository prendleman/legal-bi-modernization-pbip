# Page Build Plan

Six **core** analytic pages plus **Open & pending cases** (matter waterfall) and **Visual lab & motion** (treemap, donut, funnel, scatter + on-canvas guidance) — **eight** report tabs total — are scaffolded by the generator. See `BOOKMARKS_AND_NAV.md` and `CUSTOM_VISUALS_AND_ANIMATION.md` for bookmark and custom-visual workflows (not emitted as bookmark JSON here). Each entry below is the build recipe to flesh out further in Power BI Desktop.

## Global layout conventions

- 1280 x 720 page size (already set in scaffold), conservative grid.
- **Page chrome (generated):** one text box for title, one for subtitle, a caption **Certified extract · data through**, and a **Card** bound to `_Measures[As of date]` (scalar **date**: latest `fact_refresh_log[DateKey]` → `dim_date[Date]`, or blank if no refresh rows). Do not put formatted text in the Card — the Card visual expects numeric or date, not text.
- **Left rail:** ~268px wide so **List** / **Between** slicer headers fit at 720p; main content starts at x ≈ 296 (`scripts/pbir_visuals.py` constants).
- **Tab order:** chrome first (title → subtitle → As of), then rail slicers (low tab indices), then KPI row, then charts/tables so keyboard users reach filters before visuals.
- Body: KPI cards row below chrome, then visuals; drillthrough/detail is a Desktop follow-up.
- Use the synced **`dim_date[Date]`** **Between** slicer for the **calendar window** (axes + fact dates), and **`Time Intelligence[Time Calculation]`** for **semantics** (Current / MTD / QTD / YTD / PY / YoY) on the same measures.

### Cross-page slicer sync (`syncGroup`)

The programmatic report wires **Desktop-shaped** `syncGroup` blocks (see Supply Chain PBIR reference). Group names are fixed in `scripts/pbir_visuals.py` so a future Desktop export can be diffed without renaming:

| Group name | Field |
|---|---|
| `SidleySync_TimeCalculation` | `Time Intelligence[Time Calculation]` |
| `SidleySync_CalendarDateRange` | `dim_date[Date]` (Between) |
| `SidleySync_OfficeName` | `dim_office[OfficeName]` |
| `SidleySync_PracticeName` | `dim_practice[PracticeName]` |
| `SidleySync_ClientIndustry` | `dim_client[Industry]` |
| `SidleySync_ClientTier` | `dim_client[ClientTier]` |

After re-exporting slicers from Desktop, diff JSON against these names before changing the generator.

## Page 1 - Executive Overview

Purpose: produce polished firmwide executive BI quickly.

Visuals (generated):
- KPI cards: Total Billings, Gross Margin %, Realization Rate, Collection Rate, Migration % Complete, Refresh Success Rate.
- Line chart: Billings by MonthYear (default tooltip; optional **report page** tooltip in Desktop if you add a small hidden tooltip page).
- Column chart: Gross Margin % by practice.
- Horizontal bar: Total Billings by **industry** (`dim_client[Industry]`) — Marketing / BD mix.
- Horizontal bar: Total Billings by **client** (`dim_client[ClientName]`).

Desktop follow-ups:
- Matrix: Practice x Office with Billings, Margin %, Realization.
- Bar: optional Top N / sort by billings.
- Slicers: Date hierarchy (optional), Office, Practice, Client Tier, Time Calculation.

Talk track: Designed for CFO / COO / BI director. Shows business performance and modernization health in one view.

## Page 2 - Matter & Practice Profitability

Visuals (generated):
- Two clustered columns side by side: **Total Fees** by practice and **Realization Rate** by practice.
- **Scatter (bubble):** each **matter** (detail), **Total Fees** on X, **Gross Margin %** on Y, **WIP Amount** as size.

Desktop follow-ups:
- Matrix: Lead Partner > Practice > Client > Matter.
- Decomposition tree: Billings -> Office -> Practice -> Client Tier -> Matter Type.

Talk track: This is where the semantic model earns its keep. Finance users get one consistent definition of realization, margin, billings, WIP, and collections.

## Open & pending cases

Visuals (generated):
- KPI cards: **Open Matters** (Open + On Hold), **On Hold Matters**.
- Left rail: **Office**, **Client industry**, and **Status** (`dim_matter[MatterStatus]`) slicers bound to **`dim_matter`** denormalized fields (filters this page; not cross-synced with Executive’s `dim_office` / `dim_client` slicers—avoids ambiguous `fact_billings` paths in the model).
- **Waterfall chart:** **Open Matters** with **Category** hierarchy **OfficeName** → **ClientIndustry** (`dim_matter` denormalized fields); drill/expand on the chart to see industry within each office.
- **Detail table:** Matter number, name, office, client, lead attorney, status — **cross-filtered from the waterfall** via `page.json` `visualInteractions` (`DataFilter` both ways so clicking a bar filters the table, and selecting table rows filters the waterfall).

Desktop follow-ups: add a visual-level filter so the table hides **Closed** matters; tune interaction if your Desktop build ignores emitted `visualInteractions` (re-apply under **Format → Edit interactions**).

Talk track: Pipeline view for practice leadership—where open and held matters sit by office and client, and which lead partners carry the load.

## Page 3 - Legacy Report Migration Control Tower

Visuals (generated):
- KPI cards: Legacy Reports, Migration % Complete, Modernization Health Score.
- **Donut:** **Legacy Reports** measure by **migration status**.
- **Table:** Report name, platform, migration status, validation status, owning stakeholder group.

Desktop follow-ups:
- Stacked bar: Legacy platform x complexity.
- Matrix: Add owner, target workspace, complexity columns.
- KPI: Reports Migrated, Reports Validated, High Complexity Legacy Reports, Modernization Health Score.

Talk track: Maps directly to the Cognos / SSRS modernization need. Turns migration into a managed portfolio instead of a loose backlog.

## Page 4 - Stakeholder Requirements / KPI Catalog

Visuals (generated):
- KPI cards: Open Stakeholder Requests, SLA Breach Count.
- Slicers: Time calc, Date range, Stakeholder group, Priority (sync groups per `PAGE_BUILD_PLAN` table above).
- Table: Request title, **Product manager**, **Epic id**, stakeholder group, KPI area, priority, status, target date, acceptance criteria.

Desktop follow-ups:
- Bar: Requests by stakeholder group.
- Third KPI card: Completed Stakeholder Requests (measure exists; add in Desktop if desired).

Talk track: A BI engineer in this role operates between stakeholders and engineering. This page makes requirement intake measurable.

## Page 5 - Data Quality & Refresh Monitor

Visuals:
- KPI: Refresh Success Rate, Failed Refreshes, Avg Refresh Duration Minutes.
- Line: Refresh duration by date.
- Bar: Refresh failures by `DatasetName` and `FailureCategory`.
- Table: Latest refresh log entries (top N by date).

Talk track: Production readiness. Dashboards need observability, not just pretty visuals.

## Page 6 - RLS / Office Security Demo

Visuals:
- Office summary table.
- Text box describing role behavior.
- Cards filtered by selected office.

RLS roles already provisioned in the model (open **Modeling → Manage roles** or use **View as** on the **RLS / office security demo** page):

| Role | Filter | Demo use |
|---|---|---|
| `Chicago Office Demo` | `dim_office[OfficeName] = "Chicago"` | **View as** → Chicago-only offices and downstream facts. |
| `OfficeKey One (DAX sample)` | `dim_office[OfficeKey] = 1` | Same Chicago slice using numeric key (sample DAX pattern for dynamic RLS prep). |
| `Finance Stakeholder` | `fact_requirements_backlog[StakeholderGroup] = "Finance"` | Requirements backlog scoped to Finance. |

**One-click story:** On the RLS Demo page, compare **View as** `Chicago Office Demo` vs `OfficeKey One (DAX sample)` (identical visible rows for generated data) while the page subtitle reminds you to use Modeling → View as.

## Page 7 - Visual lab & motion

Purpose: show **native** chart variety (treemap, donut, funnel, scatter) and short **in-canvas** guidance for **custom visuals** and **bookmarks / page transitions** (see `CUSTOM_VISUALS_AND_ANIMATION.md`).

Visuals (generated): treemap (**Total Billings** by **practice**), donut (**Legacy Reports** by **migration status**), scatter (same pattern as Matter page), funnel (status × legacy count), text box with workflow notes; **Time calc** + **Date range** slicers (synced with the rest of the report).

## Bookmarks & navigation

Add a hidden navigation bookmark group so the demo runs like an app:

| Bookmark | Behavior | Use during demo |
|---|---|---|
| `Nav_Executive` | Activates Page 1, default slicers. | Opening shot. |
| `Nav_Profitability` | Page 2 with Litigation pre-selected. | Show practice depth. |
| `Nav_Migration` | Page 3 filtered to "In Build" + "Parallel Validation". | The Cognos/SSRS story. |
| `Nav_Backlog` | Page 4, P1 + Open. | Show the stakeholder muscle. |
| `Nav_Quality` | Page 5, last 90 days. | Production readiness. |
| `Nav_RLS_Chicago` | Page 6 with Chicago role explanation. | Closing security demo. |
| `Nav_VisualLab` | Visual lab page; optional bookmark after adding a custom visual in Desktop. | Native + custom visual story. |

Drillthrough:
- From Page 1 KPI cards -> Page 2 (Matter detail).
- From Page 1 Migration card -> Page 3.
- From Page 4 priority breakdown -> filtered backlog detail.

## Polish checklist before showing to a partner

- [ ] All measures use the catalog from `_Measures` (no orphan DAX in visuals).
- [ ] Format strings live on measures, not on visual properties.
- [ ] Calc group `Time Intelligence` slicer present on every analytical page; **Date range** slicer synced where emitted.
- [ ] Titles use the same font and size; no default visual titles.
- [ ] (Optional) Add a report-page tooltip with KPI summary for the Executive line chart in Desktop.
- [ ] Page 6 RLS demo shows "View as role" output explicitly.
