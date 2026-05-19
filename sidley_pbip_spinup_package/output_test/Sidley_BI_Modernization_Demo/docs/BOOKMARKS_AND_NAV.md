# Bookmarks and in-report navigation

Programmatic PBIR **bookmarks** embed a large `explorationState` (filters, visual container IDs, and projection shapes). Those IDs drift whenever visuals are regenerated, so this kit does **not** ship generated bookmark JSON files. For custom visuals and page-transition notes, see **`CUSTOM_VISUALS_AND_ANIMATION.md`**.

## Recommended approach (Power BI Desktop)

1. Open the regenerated `.pbip` after `py scripts\generate_sidley_pbip.py`.
2. Arrange slicers for each “story beat” (see `PAGE_BUILD_PLAN.md` bookmark table).
3. Use **View → Bookmarks** to create bookmarks (e.g. `Nav_Executive`, `Nav_Profitability`, …).
4. Add **buttons** or shapes with **Action → Bookmark** to jump between beats.
5. Save the project; diff `definition/bookmarks/` and `definition/pages/**/visual.json` if you want to merge patterns back into automation later.

## Date range vs Time calc

The report ships a synced **Date range** slicer (`dim_date[Date]`, Between) together with **Time calc** (`Time Intelligence[Time Calculation]`). Use **Date range** to zoom the trend (axis and fact filters); use **Time calc** for MTD / YTD / prior-year variants of measures. Bookmarks can capture both slicers when you need a fixed “MTD this month” story.

## Optional report-page tooltips

The generator does **not** emit a dedicated tooltip canvas page. If you want a richer Executive line-chart tooltip, add a small tooltip-sized page in Desktop, design visuals on it, then set **Format → Tooltip → Type → Report page** on the line chart and pick that page. Re-check the binding after major regens or visual ID changes.
