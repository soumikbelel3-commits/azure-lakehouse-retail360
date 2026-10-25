# ADR 0002: Metadata-driven ingestion with Azure Data Factory

- Status: accepted

## Context
The ERP exposes many tables. One pipeline per table would multiply code and review effort.

## Decision
A config file (`adf/config/ingestion_config.json`) lists entities, tables and watermark columns.
`PL_Master_Ingest` loops over it and calls a single parameterised `PL_Ingest_Entity`. A
tumbling-window trigger supplies the window so runs are idempotent and can be back-filled.

## Consequences
- Adding a table is a config row plus a schema entry, not a new pipeline.
- Incremental loads rely on a reliable `updated_at` style column; hard deletes in the source are
  not captured. CDC (Debezium, SAP CDC connector) is the upgrade path.
- Data is landed as files first, decoupling the source system from Databricks processing.
