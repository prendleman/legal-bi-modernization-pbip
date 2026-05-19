-- Sidley BI Modernization - gold layer DDL
-- Auto-generated. Run via the SQL warehouse to provision Delta tables.
-- Catalog : sidley_demo
-- Schema  : gold

CREATE CATALOG IF NOT EXISTS `sidley_demo` COMMENT 'Sidley BI modernization demo';
CREATE SCHEMA IF NOT EXISTS `sidley_demo`.`gold` COMMENT 'Curated gold layer feeding the Power BI semantic model';

CREATE OR REPLACE TABLE `sidley_demo`.`gold`.`dim_date` (
    `DateKey` BIGINT,
    `Date` DATE,
    `Year` BIGINT,
    `Quarter` STRING,
    `MonthNumber` BIGINT,
    `MonthName` STRING,
    `MonthYear` STRING,
    `WeekdayName` STRING,
    `IsWeekend` BIGINT,
    `IsMonthEnd` BIGINT,
    `IsHoliday` BIGINT,
    `FiscalYear` BIGINT,
    `FiscalQuarter` STRING,
    `FiscalMonth` BIGINT
)
USING DELTA
COMMENT 'Conformed date dimension (calendar + fiscal attributes).'
TBLPROPERTIES (
    'delta.columnMapping.mode' = 'name',
    'delta.minReaderVersion'  = '2',
    'delta.minWriterVersion'  = '5'
);

CREATE OR REPLACE TABLE `sidley_demo`.`gold`.`dim_office` (
    `OfficeKey` BIGINT,
    `OfficeName` STRING,
    `Region` STRING,
    `Country` STRING,
    `TimeZoneGroup` STRING
)
USING DELTA
COMMENT 'Office dimension with region/country rollups.'
TBLPROPERTIES (
    'delta.columnMapping.mode' = 'name',
    'delta.minReaderVersion'  = '2',
    'delta.minWriterVersion'  = '5'
);

CREATE OR REPLACE TABLE `sidley_demo`.`gold`.`dim_practice` (
    `PracticeKey` BIGINT,
    `PracticeName` STRING,
    `PracticeGroup` STRING
)
USING DELTA
COMMENT 'Practice and practice group dimension.'
TBLPROPERTIES (
    'delta.columnMapping.mode' = 'name',
    'delta.minReaderVersion'  = '2',
    'delta.minWriterVersion'  = '5'
);

CREATE OR REPLACE TABLE `sidley_demo`.`gold`.`dim_client` (
    `ClientKey` BIGINT,
    `ClientName` STRING,
    `Industry` STRING,
    `ClientTier` STRING,
    `RiskLevel` STRING,
    `ClientStatus` STRING
)
USING DELTA
COMMENT 'Client dimension with industry, tier, risk, status.'
TBLPROPERTIES (
    'delta.columnMapping.mode' = 'name',
    'delta.minReaderVersion'  = '2',
    'delta.minWriterVersion'  = '5'
);

CREATE OR REPLACE TABLE `sidley_demo`.`gold`.`dim_attorney` (
    `AttorneyKey` BIGINT,
    `AttorneyName` STRING,
    `AttorneyLevel` STRING,
    `OfficeKey` BIGINT,
    `PracticeKey` BIGINT,
    `StandardRate` BIGINT,
    `IsActive` BIGINT
)
USING DELTA
COMMENT 'Attorney dimension with level and standard rate.'
TBLPROPERTIES (
    'delta.columnMapping.mode' = 'name',
    'delta.minReaderVersion'  = '2',
    'delta.minWriterVersion'  = '5'
);

CREATE OR REPLACE TABLE `sidley_demo`.`gold`.`dim_matter` (
    `MatterKey` BIGINT,
    `MatterNumber` STRING,
    `MatterName` STRING,
    `ClientKey` BIGINT,
    `OfficeKey` BIGINT,
    `PracticeKey` BIGINT,
    `MatterType` STRING,
    `MatterStatus` STRING,
    `OpenDate` DATE,
    `CloseDate` STRING,
    `LeadPartnerAttorneyKey` BIGINT,
    `OfficeName` STRING,
    `ClientName` STRING,
    `ClientIndustry` STRING,
    `LeadAttorneyName` STRING
)
USING DELTA
COMMENT 'Matter dimension with type, status, lead partner; denormalized office/client/industry/lead names for matter-grain visuals.'
TBLPROPERTIES (
    'delta.columnMapping.mode' = 'name',
    'delta.minReaderVersion'  = '2',
    'delta.minWriterVersion'  = '5'
);

CREATE OR REPLACE TABLE `sidley_demo`.`gold`.`fact_billings` (
    `BillingEventKey` BIGINT,
    `DateKey` BIGINT,
    `MatterKey` BIGINT,
    `ClientKey` BIGINT,
    `OfficeKey` BIGINT,
    `PracticeKey` BIGINT,
    `BilledHours` DOUBLE,
    `FeeAmount` DOUBLE,
    `CostAmount` DOUBLE,
    `BillingAmount` DOUBLE,
    `CashCollected` DOUBLE,
    `AROutstanding` DOUBLE,
    `WIPAmount` DOUBLE,
    `DiscountAmount` DOUBLE
)
USING DELTA
COMMENT 'Monthly billing events. Grain: matter / month / event.'
TBLPROPERTIES (
    'delta.columnMapping.mode' = 'name',
    'delta.minReaderVersion'  = '2',
    'delta.minWriterVersion'  = '5'
);

CREATE OR REPLACE TABLE `sidley_demo`.`gold`.`fact_time_entries` (
    `TimeEntryKey` BIGINT,
    `DateKey` BIGINT,
    `AttorneyKey` BIGINT,
    `MatterKey` BIGINT,
    `OfficeKey` BIGINT,
    `PracticeKey` BIGINT,
    `WorkType` STRING,
    `Hours` DOUBLE,
    `StandardRate` BIGINT,
    `NarrativeQualityScore` BIGINT
)
USING DELTA
COMMENT 'Time entries. Grain: attorney / matter / day / work type.'
TBLPROPERTIES (
    'delta.columnMapping.mode' = 'name',
    'delta.minReaderVersion'  = '2',
    'delta.minWriterVersion'  = '5'
);

CREATE OR REPLACE TABLE `sidley_demo`.`gold`.`fact_legacy_report_inventory` (
    `LegacyReportKey` BIGINT,
    `LegacyReportName` STRING,
    `LegacyPlatform` STRING,
    `OwningStakeholderGroup` STRING,
    `OwningOfficeKey` BIGINT,
    `OwningPracticeKey` BIGINT,
    `Complexity` STRING,
    `MigrationStatus` STRING,
    `ValidationStatus` STRING,
    `EstimatedHoursRemaining` BIGINT,
    `UsageScore` BIGINT,
    `TargetWorkspace` STRING,
    `ReplacementReportName` STRING
)
USING DELTA
COMMENT 'Legacy report migration tracker (Cognos / SSRS / etc.).'
TBLPROPERTIES (
    'delta.columnMapping.mode' = 'name',
    'delta.minReaderVersion'  = '2',
    'delta.minWriterVersion'  = '5'
);

CREATE OR REPLACE TABLE `sidley_demo`.`gold`.`fact_requirements_backlog` (
    `RequirementKey` BIGINT,
    `RequestTitle` STRING,
    `ProductManager` STRING,
    `EpicId` STRING,
    `StakeholderGroup` STRING,
    `OfficeKey` BIGINT,
    `PracticeKey` BIGINT,
    `KPIArea` STRING,
    `Priority` STRING,
    `RequestStatus` STRING,
    `CreatedDate` DATE,
    `TargetDate` DATE,
    `SLABreachFlag` BIGINT,
    `AcceptanceCriteria` STRING
)
USING DELTA
COMMENT 'Stakeholder analytics request backlog.'
TBLPROPERTIES (
    'delta.columnMapping.mode' = 'name',
    'delta.minReaderVersion'  = '2',
    'delta.minWriterVersion'  = '5'
);

CREATE OR REPLACE TABLE `sidley_demo`.`gold`.`fact_refresh_log` (
    `RefreshLogKey` BIGINT,
    `DateKey` BIGINT,
    `DatasetName` STRING,
    `RefreshStatus` STRING,
    `DurationMinutes` DOUBLE,
    `RowsProcessed` BIGINT,
    `FailureCategory` STRING
)
USING DELTA
COMMENT 'Dataset refresh observability log.'
TBLPROPERTIES (
    'delta.columnMapping.mode' = 'name',
    'delta.minReaderVersion'  = '2',
    'delta.minWriterVersion'  = '5'
);
