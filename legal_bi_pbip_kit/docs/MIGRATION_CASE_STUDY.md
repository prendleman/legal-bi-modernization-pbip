# Migration case study - retiring "Monthly Billings by Practice" from Cognos

A 1-page worked example showing how a single legacy report gets through the **Migration Control Tower** that this demo models.

The report, owner, and dates below are **invented for the demo**. The point is the **mechanics**: how the entry in `fact_legacy_report_inventory` evolves, what `fact_requirements_backlog` captures alongside it, and how `Modernization Health Score` ticks up when the row reaches `Retired`.

## The legacy report

| Field | Value |
| --- | --- |
| `LegacyReportID` | `CG-FIN-0421` |
| `LegacyPlatform` | `Cognos 11` |
| `LegacyReportName` | `Monthly Billings by Practice` |
| `OwnerBusinessUnit` | `Finance` |
| `OwnerName` | `J. Castille (Finance Ops)` |
| `Audience` | `Firm Leadership + Practice Heads` |
| `RefreshCadence` | `Monthly` |
| `Complexity` | `High` |
| `RowCountApprox` | `~80,000 fee rows/month` |
| `MigrationStatus` | `Identified` -> `In Build` -> `In Validation` -> `Migrated` -> `Retired` |
| `ValidationStatus` | `Not Started` -> `In Progress` -> `Validated` |

## Step 0 - Identification (Migration Control Tower picks it up)

The row is created in `fact_legacy_report_inventory` with `MigrationStatus = "Identified"` after Finance Ops surfaces it during the legacy inventory drive. The Migration Control Tower page filters to `Complexity = "High"` and surfaces it as a top-10 candidate.

`Modernization Health Score` is unaffected (no migration progress yet).

## Step 1 - Discovery and acceptance criteria

The BI team opens a row in `fact_requirements_backlog`:

| Field | Value |
| --- | --- |
| `RequirementID` | `REQ-2026-Q2-007` |
| `StakeholderGroup` | `Finance` |
| `RequestTitle` | `Replace Cognos "Monthly Billings by Practice" with certified PBIP equivalent` |
| `Priority` | `High` |
| `AcceptanceCriteria` | `Practice rollup matches Cognos to within $1 across 6 months of parallel runs; PY and YoY columns match Finance's existing calc; RLS prevents non-Finance roles from seeing margin %; refresh completes < 20 min on Test workspace.` |
| `RequestStatus` | `In Discovery` |
| `TargetDate` | `2026-07-31` |

Discovery confirms the source-of-truth column choices that go into the certified semantic model:

- Use `fact_billings[FeeAmount]` (not `BillingAmount`) for the practice rollup, matching the Finance definition of "fees ex-disbursements."
- `dim_practice[PracticeName]` is the slicer; surrogate keys never appear in the report.
- The Cognos report's "PY" column maps to the calc group item `Time Intelligence[Time Calculation] = "PY"` applied to `[Total Fees]`.

`MigrationStatus` advances to `In Build`.

## Step 2 - Build (Power BI + lakehouse)

The work that lands in the PBIP:

- A new page **"Finance - Billings by Practice"** based on the existing Finance page template (page chrome reused, see `PAGE_BUILD_PLAN.md`).
- No new measures needed - `[Total Fees]`, `[Gross Margin %]`, and the calc group already cover the Cognos column set (see `DAX_DEEP_DIVE.md` for why measures are independent).
- A `Between` slicer on `dim_date[Date]` for the calendar window and a single-select slicer on `Time Intelligence[Time Calculation]`.
- The Databricks pipeline already publishes `fact_billings` to `sidley_demo.gold.fact_billings`. The PBIP toggles to the lakehouse via `pDataSource = "Databricks"` (see `DATABRICKS_INTEGRATION.md`).
- Page-level filter for `dim_practice[Active] = TRUE` so retired practice codes do not appear, matching what Cognos filtered server-side.

CI: `scripts/smoke_pbip.py` passes; `data_quality_report.md` shows PASS on FK/PK across the affected tables.

## Step 3 - Parallel validation (the longest step)

`MigrationStatus = "In Validation"`, `ValidationStatus = "In Progress"`.

Finance Ops runs the Cognos report and the PBIP side by side for **one full reporting cycle** (a calendar month plus its month-end close window). The BI team records the comparison in a parallel-validation worksheet (lives outside the demo).

Acceptance criteria pass:

- Practice rollup matches Cognos to within $0.42 across 6 months (rounding from Cognos casting `FeeAmount` to `NUMERIC(18, 2)` mid-pipeline; documented and accepted).
- PY column matches month-by-month after the BI team adjusts for a Cognos quirk that treated October 2023 as the PY anchor for November 2024 reporting.
- RLS verified via **Modeling -> View as roles**: Finance Stakeholder role sees all practices; Chicago Office Demo role sees the same data but is reminded by the Refresh Monitor page that this report is firmwide.
- Refresh on Test workspace averages 9 minutes (under the 20-minute SLA).

Sign-off recorded against `RequirementID = REQ-2026-Q2-007`.

`ValidationStatus = "Validated"`. `Modernization Health Score` moves: the `Validation % Complete` component picks up one more row in the numerator.

## Step 4 - Promotion (Test -> Prod)

Promotion checklist from `DEPLOYMENT.md` is satisfied:

1. Data quality PASS.
2. Latest scheduled refresh on Test succeeded.
3. Stakeholder sign-off captured on `REQ-2026-Q2-007`.
4. Parallel validation captured (`ValidationStatus = "Validated"`).
5. RLS roles re-tested.
6. The certified semantic model is the only data source.

The deployment pipeline promotes the dataset and report to Prod; the data-source parameters `pDataSource`, `pDatabricksHost`, `pDatabricksHttpPath`, `pDatabricksCatalog`, and `pDatabricksSchema` are overridden per stage so no file edits ship.

`MigrationStatus = "Migrated"`.

## Step 5 - Retirement

Finance Ops:

- Communicates the cutover to subscribers (this lives outside the demo but is captured in `RECRUITER_HANDOFF.md`-style runbook artifacts in a real tenant).
- Removes Cognos subscriptions and access to `CG-FIN-0421`.

BI team:

- Sets `MigrationStatus = "Retired"`, `RetiredDate = 2026-08-15`.
- Removes the report from the Cognos environment after a 30-day grace window for cached subscribers.

`Modernization Health Score` updates: `Migration % Complete` numerator goes up by one row.

## What the score actually does

Concrete numbers, illustrative:

- Before this report retires: 31 / 80 legacy reports retired, 28 / 80 validated, refresh success rate 99.2%.
  - `Migration % Complete` = 38.8% -> contributes 15.5 of 40.
  - `Validation % Complete` = 35.0% -> contributes 10.5 of 30.
  - `Refresh Success Rate` = 99.2% -> contributes 29.8 of 30.
  - `Modernization Health Score` = **55.8**.
- After `CG-FIN-0421` is retired and validated:
  - `Migration % Complete` = 40.0% -> 16.0 of 40.
  - `Validation % Complete` = 36.3% -> 10.9 of 30.
  - `Refresh Success Rate` unchanged -> 29.8 of 30.
  - `Modernization Health Score` = **56.7**.

Less than one point on the gauge per retired report, by design. The point is that **each retirement is auditable, defensible, and reversible**, not that the score sprints upward.

## Related

- [`DAX_DEEP_DIVE.md`](DAX_DEEP_DIVE.md) - why `Modernization Health Score` uses the weights it does.
- [`DEPLOYMENT.md`](DEPLOYMENT.md) - the Dev/Test/Prod promotion mechanics referenced above.
- [`DATABRICKS_INTEGRATION.md`](DATABRICKS_INTEGRATION.md) - the lakehouse path used in Step 2.
- [`PAGE_BUILD_PLAN.md`](PAGE_BUILD_PLAN.md) - the page chrome and slicer pattern reused here.
- [`AI_GOVERNANCE.md`](AI_GOVERNANCE.md) - certification + RLS controls invoked in Step 3.
