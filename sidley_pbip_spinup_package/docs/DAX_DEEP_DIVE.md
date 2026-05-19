# DAX deep dive

The full measure catalog lives in [`DAX_MEASURES.dax`](DAX_MEASURES.dax) and is emitted into `model.bim` by `scripts/generate_sidley_pbip.py`. This document picks four measures and explains the design choices behind them - the kind of conversation a Senior BIE interview tends to probe.

## 1. `Realization Rate` - why two SUMs, not a stored ratio

```dax
Realization Rate = DIVIDE ( [Billed Hours], [Billable Hours] )
```

with

```dax
Billed Hours = SUM ( fact_billings[BilledHours] )

Billable Hours =
CALCULATE (
    SUM ( fact_time_entries[Hours] ),
    fact_time_entries[WorkType] = "Billable"
)
```

**Design choice:** keep numerator and denominator as **independent measures**, never as a precomputed column or a single combined expression.

**Why:**

- Slicer composition: a slicer on `dim_practice` filters `Billed Hours` and `Billable Hours` independently and the ratio recomputes correctly. A stored ratio would have to be re-aggregated, and a weighted average of ratios is not a ratio of weighted averages.
- Visual reuse: the same `Billed Hours` and `Billable Hours` measures show up on Productivity, Practice, and Matter pages alongside the rate, without redefining the components.
- Time-intelligence pickup: the calc group's `YTD` / `YoY` items wrap `SELECTEDMEASURE()`, so they apply uniformly to numerator and denominator when this measure is placed on a time axis.
- `DIVIDE` returns BLANK on zero denominator. That makes empty cells render as blanks instead of `#NUM` and avoids visual error states for sparsely populated practices.

**Common alternative I would reject:** a calculated column `IsBilled = fact_time_entries[WorkType] = "Billable"` plus `SUM ( fact_time_entries[BilledHourCalc] )`. That bakes the filter into the row context and forfeits the cross-filter flexibility - it would not respect a future `IS_BILLABLE_OVERRIDE` flag without recomputing the column at refresh.

## 2. `Refresh Success Rate` - a quality measure that doubles as a SLO

```dax
Refresh Events = COUNTROWS ( fact_refresh_log )

Successful Refreshes =
CALCULATE (
    COUNTROWS ( fact_refresh_log ),
    fact_refresh_log[RefreshStatus] = "Success"
)

Refresh Success Rate = DIVIDE ( [Successful Refreshes], [Refresh Events] )
```

**Design choice:** anchor observability in a fact table, not in PowerShell or Log Analytics.

**Why:**

- Same semantic model owns the metric. The BI team does not depend on a side channel to know whether the model is healthy.
- The KPI composes with `dim_date` and `dim_office`, so a stand-up can ask "Chicago this week" rather than "the firmwide success rate."
- The same rollup feeds `Modernization Health Score` (below), which is the single number shown to firm leadership.
- Pairs with `FailureCategory` slicers (Gateway / Credential / Schema Drift / Timeout / Source Unavailable) so an outage discussion has the *why*, not just the *what*.

**Operational use:** the threshold for promotion (Test -> Prod) and for paging the BI on-call live in `docs/DEPLOYMENT.md`. They do **not** live in DAX - DAX surfaces the signal; runbooks own the action.

## 3. `Modernization Health Score` - the boardroom KPI

```dax
Modernization Health Score =
VAR MigrationScore   = [Migration % Complete]   * 40
VAR ValidationScore  = [Validation % Complete]  * 30
VAR RefreshScore     = [Refresh Success Rate]   * 30
RETURN
    MigrationScore + ValidationScore + RefreshScore
```

**Design choice:** explicit weights (40 / 30 / 30), `VAR` decomposition, no fancy normalization.

**Why:**

- Variables make the weighting **legible**. A reviewer reads the recipe in seconds. A nested expression would force them to keep ratios in their head.
- The weights sum to 100, so the result is a 0-100 score that lines up with the gauge visual on the Executive page. No additional `DIVIDE` or `MIN`/`MAX` clamp is needed - the inputs are all percentages by construction.
- It is **boring on purpose**. Composite KPIs that get clever (geometric means, conditional weights) lose stakeholder trust the moment a number moves and nobody can explain why. The Migration Control Tower needs to be defensible in a partner meeting.
- The composition makes the trade-off visible. If refresh reliability tanks, leadership sees the score drop and the BI team can point at `fact_refresh_log` for the proof. If migration stalls, same pattern.

**Where I would extend it:** add stakeholder-satisfaction inputs once `fact_requirements_backlog[SLABreachFlag]` has enough history to be meaningful (currently shown but not yet weighted in).

## 4. `As of date` - the smallest measure that solves the most-asked question

```dax
As of date =
VAR lk =
    CALCULATE ( MAX ( fact_refresh_log[DateKey] ), REMOVEFILTERS () )
RETURN
    IF ( ISBLANK ( lk ), BLANK (), LOOKUPVALUE ( dim_date[Date], dim_date[DateKey], lk ) )
```

**Design choice:** **scalar** date, not a text label, evaluated against the **unfiltered** `fact_refresh_log`.

**Why:**

- The page chrome uses a **Card** visual for "data through". Classic Cards do not render text measures - they error out - so this measure returns a **date** value with a `yyyy-MM-dd` format string. The Card renders cleanly with no fallback to "1 item" placeholder text.
- `REMOVEFILTERS ()` is intentional. A user slicing the page to one office should still see the **overall freshness** of the model, not the freshness of just that office's refresh subset. The freshness story belongs to the model as a whole.
- `LOOKUPVALUE` from `dim_date` keeps the result locale-aware and date-typed; sorting and time-intel still apply if someone drops it on a time axis later.
- One measure replaces a "When did this refresh?" question per stakeholder per week.

## Patterns the rest of the model relies on

| Pattern | Where it shows up | Why |
| --- | --- | --- |
| Independent numerator + denominator measures with `DIVIDE` | `Realization Rate`, `Billable %`, `Gross Margin %`, `Collection Rate`, `Migration % Complete`, `Validation % Complete`, `Refresh Success Rate` | Slicer composition + time-intel uniformity (see #1). |
| Filter measures via `CALCULATE` + status / category column | `Open Matters`, `Reports Migrated`, `Reports Validated`, `Open Stakeholder Requests`, `SLA Breach Count`, `Failed Refreshes` | Keeps row counts and category filters in the measure layer where they can be reused across pages. |
| Calc group `Time Intelligence[Time Calculation]` wrapping `SELECTEDMEASURE()` | Every Financial / Productivity / Quality measure | One calc group ships Current / MTD / QTD / YTD / PY / PYTD / YoY / YoY % for every measure - no per-measure variant explosion. |
| `Between` slicer on `dim_date[Date]` for the calendar window | All time-axis visuals | The calc group selects **semantics**; the slicer selects the **window**. Decoupled. |
| `VAR` decomposition for composite KPIs | `Modernization Health Score` (and forward-looking weighted scores) | Legibility for stakeholders; reduces churn when weights are tuned. |
| Display folders + format strings emitted from Python | All measures | A single dict drives `model.bim` + `DAX_MEASURES.dax` + `gold_layer_ddl.sql`, so schema and measure layout cannot drift. |

## What I would do differently in a real Sidley engagement

1. Replace the static 40/30/30 weights in `Modernization Health Score` with **stakeholder-tuned weights** captured in a parameter table the Practice Leadership group can edit.
2. Add a **detached date table** for "comparison period" so the calc group's `PY` and `YoY` items can shift against any user-selected anchor (typical for firms whose fiscal year does not align to calendar year).
3. Promote `Modernization % Complete` and `Refresh Success Rate` to **certified measures** in the workspace, so any thin report that consumes them inherits the same definition.
4. Add **`USERELATIONSHIP`** measures for `fact_billings` against `dim_date` on both `BillingDate` and `MatterOpenDate` (currently single active relationship; the inactive role would unlock an "by matter cohort" view).
