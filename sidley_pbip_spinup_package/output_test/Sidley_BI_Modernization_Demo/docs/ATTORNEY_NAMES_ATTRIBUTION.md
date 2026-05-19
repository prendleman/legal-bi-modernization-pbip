# Attorney names in the demo data

## Source

Public **display names** are maintained in:

`sidley_pbip_spinup_package/scripts/report_assets/sidley_public_attorney_names.json`

That file lists **URLs** of Sidley Austin LLP web pages (Management Committee and Executive Committee directories) from which names were transcribed. It is **not** an automated scrape of the live site on every build: refresh the JSON manually if leadership pages change.

## Intended use

- **Interview realism only** — so charts and slicers show recognizable firm leadership instead of `Attorney 001`.
- **All facts are synthetic** — matters, billings, hours, backlog rows, and refresh logs are generated; they must **not** be read as real firm metrics for any person named.

## Ethics / interview line

> I pulled public directory names into a static JSON so the demo feels grounded, but every numeric and status is fake seed data — I would never ship real lawyer performance off a public roster without governance and consent.

## Technical behavior

`generate_sidley_pbip.py` loads the JSON when present. Rows `1 … len(display_names)` use each name once; additional synthetic attorney rows append `(demo roster NNN)` so `AttorneyName` stays unique for `AttorneyKey`.

If the JSON file is missing, the generator logs a warning and falls back to `Attorney ###` labels.
