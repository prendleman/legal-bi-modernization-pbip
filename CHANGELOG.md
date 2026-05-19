# Changelog

All notable changes to this repository will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `previews/` folder with data previews generated from synthetic gold CSVs:
  - 8 per-page PNGs in `previews/pages/` rendered by `sidley_pbip_spinup_package/scripts/render_page_previews.py` (matplotlib + pandas).
  - Single-page HTML dashboard mockup at `previews/dashboard_mockup.html` rendered by `sidley_pbip_spinup_package/scripts/build_html_mockup.py` (pandas + inline SVG, no extra deps).
  - `previews/README.md` explains what these are (data previews, not Power BI screenshots), what the real PBIP build adds on top, and how to regenerate.
- `sidley_pbip_spinup_package/requirements-preview.txt` pinning matplotlib + pandas for the preview pipeline.
- Both root and package READMEs now embed the previews so the GitHub landing page is skim-friendly without launching Power BI Desktop.

### Planned

- Power BI Desktop screenshots of all 8 report pages embedded alongside the previews.
- RLS "View as role" comparison screenshots.

## [0.1.0] - 2026-05-19

### Added

- Initial public release of the Legal BI Modernization PBIP Demo Kit.
- One-command PBIP generator: `sidley_pbip_spinup_package/scripts/generate_sidley_pbip.py`.
- 8-page PBIP report + TMSL semantic model (`model.bim`) with measures, calc group, hierarchies, three RLS roles, and Power Query parameters.
- Two-mode data source: local CSV (default) or Databricks SQL Warehouse via `pDataSource` parameter.
- Databricks integration: idempotent Unity Catalog provisioning, gold-layer DDL emission, CSV upload to UC volume, and `COPY INTO` of Delta tables (`--databricks`, with `--dry-run`).
- Bronze -> silver -> gold notebook (`docs/databricks_notebook.py`).
- Documentation set: `MODEL_DESIGN.md`, `PAGE_BUILD_PLAN.md`, `DAX_MEASURES.dax`, `BOOKMARKS_AND_NAV.md`, `CUSTOM_VISUALS_AND_ANIMATION.md`, `INTERVIEW_TALK_TRACK.md`, `JD_TO_DEMO_MAP.md`, `CERT_PREP.md`, `RECRUITER_HANDOFF.md`, `DATABRICKS_INTEGRATION.md`, `DEPLOYMENT.md`, `ATTORNEY_NAMES_ATTRIBUTION.md`, `SQL_GOLD_LAYER_SAMPLES.sql`, `data_quality_report.md`.
- Databricks productionization scaffolding: `docs/PRODUCTIONIZATION_UC_MLFLOW.md`, `docs/AI_GOVERNANCE.md`, `databricks/asset_bundle/databricks.template.yml`, `databricks/asset_bundle/README.md`.
- Migration case study (`docs/MIGRATION_CASE_STUDY.md`) and DAX deep dive (`docs/DAX_DEEP_DIVE.md`).
- CI: GitHub Actions workflow `.github/workflows/validate.yml` running `scripts/smoke_pbip.py` on push and PR.
- Dependabot config (`.github/dependabot.yml`) for pip and GitHub Actions.
- Top-level `README.md`, `LICENSE` (MIT + Sidley disclaimer), `SECURITY.md`, `.gitignore`, `.gitattributes`.

[Unreleased]: https://github.com/prendleman/legal-bi-modernization-pbip/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/prendleman/legal-bi-modernization-pbip/releases/tag/v0.1.0
