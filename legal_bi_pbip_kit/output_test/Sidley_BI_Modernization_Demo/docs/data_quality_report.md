# Data Quality Report

- Generated: 2026-05-01T21:51:08Z
- Seed: 42
- Date range: 2023-01-01 -> 2026-04-30

| Check | Status | Detail |
|---|---|---|
| row_count[dim_date] | PASS | 1,216 rows |
| row_count[dim_office] | PASS | 7 rows |
| row_count[dim_practice] | PASS | 8 rows |
| row_count[dim_client] | PASS | 180 rows |
| row_count[dim_attorney] | PASS | 120 rows |
| row_count[dim_matter] | PASS | 450 rows |
| row_count[fact_billings] | PASS | 3,356 rows |
| row_count[fact_time_entries] | PASS | 26,000 rows |
| row_count[fact_legacy_report_inventory] | PASS | 150 rows |
| row_count[fact_requirements_backlog] | PASS | 110 rows |
| row_count[fact_refresh_log] | PASS | 750 rows |
| dim_date.coverage | PASS | 1216 rows for 1216 expected days |
| fk_integrity[fact_billings.DateKey -> dim_date.DateKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_billings.MatterKey -> dim_matter.MatterKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_billings.ClientKey -> dim_client.ClientKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_billings.OfficeKey -> dim_office.OfficeKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_billings.PracticeKey -> dim_practice.PracticeKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_time_entries.DateKey -> dim_date.DateKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_time_entries.MatterKey -> dim_matter.MatterKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_time_entries.AttorneyKey -> dim_attorney.AttorneyKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_time_entries.OfficeKey -> dim_office.OfficeKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_time_entries.PracticeKey -> dim_practice.PracticeKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_legacy_report_inventory.OwningOfficeKey -> dim_office.OfficeKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_legacy_report_inventory.OwningPracticeKey -> dim_practice.PracticeKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_requirements_backlog.OfficeKey -> dim_office.OfficeKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_requirements_backlog.PracticeKey -> dim_practice.PracticeKey] | PASS | 0 orphan(s) |
| fk_integrity[fact_refresh_log.DateKey -> dim_date.DateKey] | PASS | 0 orphan(s) |
| fk_integrity[dim_matter.ClientKey -> dim_client.ClientKey] | PASS | 0 orphan(s) |
| fk_integrity[dim_matter.OfficeKey -> dim_office.OfficeKey] | PASS | 0 orphan(s) |
| fk_integrity[dim_matter.PracticeKey -> dim_practice.PracticeKey] | PASS | 0 orphan(s) |
| fk_integrity[dim_attorney.OfficeKey -> dim_office.OfficeKey] | PASS | 0 orphan(s) |
| fk_integrity[dim_attorney.PracticeKey -> dim_practice.PracticeKey] | PASS | 0 orphan(s) |
| pk_unique[dim_date.DateKey] | PASS | 0 duplicate(s) |
| pk_unique[dim_office.OfficeKey] | PASS | 0 duplicate(s) |
| pk_unique[dim_practice.PracticeKey] | PASS | 0 duplicate(s) |
| pk_unique[dim_client.ClientKey] | PASS | 0 duplicate(s) |
| pk_unique[dim_attorney.AttorneyKey] | PASS | 0 duplicate(s) |
| pk_unique[dim_matter.MatterKey] | PASS | 0 duplicate(s) |

All checks passed.
