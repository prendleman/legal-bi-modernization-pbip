# AI and BI governance - Sidley demo framing

This document captures the **governance and Responsible AI design intent** for the Sidley legal-BI modernization demo.

It is **not** a substitute for the firm's IT, Risk, and Office of General Counsel programs - it shows what the demo demonstrates today and where production controls would live.

The synthetic data in this repo is invented; only public Sidley.com attorney names appear (see `ATTORNEY_NAMES_ATTRIBUTION.md`). No real client, matter, or billing data is used.

## Data classification

| Class | Example in this demo | Handling |
| --- | --- | --- |
| Public / synthetic | All CSVs in `data/` | Safe to share; clearly labeled as synthetic in `README.md` and `data_quality_report.md`. |
| Internal (real tenant) | **Not present** | Would require Unity Catalog policies, encryption at rest, and access reviews tied to AD groups. |
| Client-confidential (matter data) | **Not modeled** | Real deployments need ethical walls, conflict checks, and matter-team-only access via dynamic RLS. |
| Privileged / work-product | **Not modeled** | Excluded from BI scope; analytics describe billing and operational metadata only. |

## Row-level security (implemented in demo)

The semantic model ships **three** sample roles to anchor the conversation about ethical walls and office-scoped access:

| Role | Filter | Production analog |
| --- | --- | --- |
| Chicago Office Demo | `dim_office[OfficeName] = "Chicago"` | Office-scoped RLS for office heads. |
| OfficeKey One (DAX sample) | `dim_office[OfficeKey] = 1` | Same office cut via the surrogate key path. |
| Finance Stakeholder | `fact_requirements_backlog[StakeholderGroup] = "Finance"` | Stakeholder-scoped backlog view. |

Production RLS adds (see `DEPLOYMENT.md`):

- Practice Leadership (filtered to `dim_practice`).
- Marketing / BD (filtered to `fact_requirements_backlog`).
- Firm Leadership (no filter).
- Dynamic Office (joined on an `office_user_map` table keyed by `USERPRINCIPALNAME`).

## Certification and promotion

| Control | Where it lives | Production expectation |
| --- | --- | --- |
| Certified semantic model | `Sidley_BI_Modernization_Demo.SemanticModel/model.bim` | Only certified datasets feed thin reports; legacy duplicates are retired via the Migration Control Tower. |
| Promotion checklist | `DEPLOYMENT.md` (Test -> Prod) | Sign-off captured against `fact_requirements_backlog` acceptance criteria. |
| Legacy retirement | `fact_legacy_report_inventory` + Migration Control Tower page | Cognos / SSRS access removed only after `ValidationStatus = "Validated"`. |

## Refresh observability

| Signal | Tooling in demo | Production expectation |
| --- | --- | --- |
| Refresh success rate | `fact_refresh_log` + Refresh Monitor page | Alert when below threshold; freeze promotions until cleared. |
| Failure categorization | `FailureCategory` (Gateway / Credential / Schema Drift / Timeout / Source Unavailable) | Routed to BI / DE on-call rotations. |
| Data-quality gates | `data_quality_report.md` regenerated on every build | Treat FK / PK / coverage failures as release blockers. |
| Schema drift | DDL emitted from the same dict that builds `model.bim` | Pre-deploy diff against UC table schemas; fail the bundle if mismatch. |

## Audit trail fields

Gold tables carry the audit columns the BI team needs for drill-through and post-incident review:

- `RefreshID`, `RefreshStartTimeUTC`, `RefreshEndTimeUTC`, `Status`, `FailureCategory` (in `fact_refresh_log`)
- `LegacyReportID`, `ValidationStatus`, `RetiredDate` (in `fact_legacy_report_inventory`)
- `RequirementID`, `StakeholderGroup`, `AcceptanceCriteria`, `Status`, `TargetDate` (in `fact_requirements_backlog`)

These support **BI drill-through** and **operational review**. Legal-discovery-grade audit logging is a separate firm IT control.

## AI / Copilot positioning (design intent)

The Sidley demo does **not** publish a Copilot agent. AI surfaces appear as:

- **Talking-point design**: how a future Copilot for Power BI experience would ground answers in the certified semantic model and respect office/practice RLS automatically.
- **Backlog signals**: `fact_requirements_backlog` is the place where AI-assisted intake (summarization, classification) would land for the BI team.
- **Forecasting hook**: see `PRODUCTIONIZATION_UC_MLFLOW.md` for the MLflow shape a future matter-fee forecast or time-entry anomaly model would take.

No tenant agent, prompt, or grounding contract is shipped in this repo.

## Responsible AI checklist (when models arrive)

When the first predictive model lands (forecast, anomaly, classification), the BI team would document:

1. **Intended use** and out-of-scope use cases.
2. **Data lineage**: source -> bronze -> silver -> gold -> feature table.
3. **Performance**: hold-out metrics, sub-group performance, and decision thresholds.
4. **Fairness review**: practice / office / attorney-tenure slices, with sign-off from Risk.
5. **Refresh cadence**: who retrains, on what schedule, and how stage transitions are gated.
6. **Override path**: how partners and BI engineers can flag and disable model-driven outputs.

## Related

- [`docs/DEPLOYMENT.md`](DEPLOYMENT.md)
- [`docs/PRODUCTIONIZATION_UC_MLFLOW.md`](PRODUCTIONIZATION_UC_MLFLOW.md)
- [`docs/DATABRICKS_INTEGRATION.md`](DATABRICKS_INTEGRATION.md)
- [`docs/ATTORNEY_NAMES_ATTRIBUTION.md`](ATTORNEY_NAMES_ATTRIBUTION.md)
