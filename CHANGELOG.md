# Changelog

All notable changes to this repository will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Power BI Desktop screenshots of all 8 report pages in `screenshots/` and embedded in both READMEs.
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
