# Custom visuals, native variety, and motion

This note complements **`BOOKMARKS_AND_NAV.md`**. The generator favors **built-in visuals** so PBIP regen stays stable; custom visuals and heavy animation are handled in **Desktop** with a clear merge path.

## Native “sophisticated” visuals (in repo)

The scaffold adds richer **built-in** types where they support the talk track:

| Visual | Where | Role |
|--------|--------|------|
| **Scatter** (bubble) | Matter & profitability, Visual lab | `dim_matter[MatterName]` as details; **Total Fees** vs **Gross Margin %**; **WIP Amount** sizes bubbles. |
| **Treemap** | Visual lab | **Total Billings** by **practice**. |
| **Donut** | Legacy migration, Visual lab | **Legacy Reports** by **migration status**. |
| **Funnel** | Visual lab | Same status dimension (ordered funnel stages in Desktop if needed). |

After `py scripts\generate_legal_bi_pbip.py`, open the PBIP in Power BI Desktop once. If a visual shows a field-well error, the query role name may differ slightly by Desktop version — fix in Desktop, **Save**, then diff the emitted `visual.json` and port the change into `scripts/pbir_visuals.py`.

## Custom visuals (AppSource / org store)

1. In **Desktop**, enable the visual from **Get more visuals** (tenant policy permitting).
2. Place it on a page, bind fields, format as desired.
3. **Save** the PBIP.
4. Diff `definition/pages/**/visuals/*/visual.json` and any new files under `StaticResources/RegisteredResources/` (custom visuals often register a resource package).
5. **Do not** blindly re-run the generator over hand-edited pages unless you merge those fragments back into `pbir_visuals.py` or exclude that page from codegen.

Certified visuals are preferred for **service** deployment and **export data** behavior. Keep a short allowlist for production tenants.

## Animation and “motion”

Power BI does not offer timeline-style chart animation like D3. Practical options:

- **Bookmarks** (View → Bookmarks): capture slicer state, **Data** vs **Display** options, and selected visuals. Wire **buttons** with **Action → Bookmark** for a stepped demo (see `BOOKMARKS_AND_NAV.md`).
- **Page transitions**: **View → Page transitions** (fade, push, etc.) — set per report in Desktop; PBIR may store these on save. Regenerating the report from Python does not currently emit transition JSON; re-apply after regen or add a post-gen merge step.
- **Play axis** (scatter): optional in Desktop on the scatter chart for time-phased playback when a date/hierarchy is added to the play field — not emitted by default in this kit.

## CI

`py scripts\smoke_pbip.py` validates JSON parse and page count only — it does **not** load custom visuals or validate field wells against the engine.
