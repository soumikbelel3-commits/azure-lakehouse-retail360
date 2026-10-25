-- Unity Catalog foundation for one environment. Run once per environment, as a metastore admin,
-- after `terraform apply`. Placeholders are substituted by scripts/render_sql.sh:
--   __CATALOG__          retail360_dev | retail360_prod
--   __STORAGE_ACCOUNT__  terraform output storage_account_name
--
-- Prerequisite (not expressible in SQL for Azure managed identities): a storage credential that
-- wraps the Databricks access connector created by Terraform:
--   databricks storage-credentials create --json '{
--     "name": "retail360_mi",
--     "azure_managed_identity": {"access_connector_id": "<terraform output databricks_access_connector_id>"}
--   }'

-- ---------------------------------------------------------------------------------------
-- External locations: one per lakehouse zone, all backed by the same storage credential
-- ---------------------------------------------------------------------------------------
CREATE EXTERNAL LOCATION IF NOT EXISTS retail360_landing
  URL 'abfss://landing@__STORAGE_ACCOUNT__.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL retail360_mi)
  COMMENT 'Raw files delivered by Data Factory';

CREATE EXTERNAL LOCATION IF NOT EXISTS retail360_checkpoints
  URL 'abfss://checkpoints@__STORAGE_ACCOUNT__.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL retail360_mi)
  COMMENT 'Auto Loader schemas and streaming checkpoints';

CREATE EXTERNAL LOCATION IF NOT EXISTS retail360_bronze
  URL 'abfss://bronze@__STORAGE_ACCOUNT__.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL retail360_mi);

CREATE EXTERNAL LOCATION IF NOT EXISTS retail360_silver
  URL 'abfss://silver@__STORAGE_ACCOUNT__.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL retail360_mi);

CREATE EXTERNAL LOCATION IF NOT EXISTS retail360_gold
  URL 'abfss://gold@__STORAGE_ACCOUNT__.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL retail360_mi);

-- ---------------------------------------------------------------------------------------
-- Catalog and schemas. Each schema stores its managed tables in its own zone container, so the
-- physical layout mirrors the medallion layers.
-- ---------------------------------------------------------------------------------------
CREATE CATALOG IF NOT EXISTS __CATALOG__
  COMMENT 'Retail 360 lakehouse';

CREATE SCHEMA IF NOT EXISTS __CATALOG__.bronze
  MANAGED LOCATION 'abfss://bronze@__STORAGE_ACCOUNT__.dfs.core.windows.net/managed'
  COMMENT 'Append-only raw data with lineage columns';

CREATE SCHEMA IF NOT EXISTS __CATALOG__.silver
  MANAGED LOCATION 'abfss://silver@__STORAGE_ACCOUNT__.dfs.core.windows.net/managed'
  COMMENT 'Typed, de-duplicated, PII-minimised data; quarantine tables for rejected rows';

CREATE SCHEMA IF NOT EXISTS __CATALOG__.gold
  MANAGED LOCATION 'abfss://gold@__STORAGE_ACCOUNT__.dfs.core.windows.net/managed'
  COMMENT 'Star schema and aggregates for BI and ML';

-- ---------------------------------------------------------------------------------------
-- Access model (account-level groups synced from Microsoft Entra ID)
--   data-engineers    build and operate the pipelines
--   data-analysts     read the Gold layer
--   data-scientists   read Silver and Gold
-- ---------------------------------------------------------------------------------------
GRANT USE CATALOG ON CATALOG __CATALOG__ TO `data-engineers`, `data-analysts`, `data-scientists`;

GRANT USE SCHEMA, SELECT, MODIFY, CREATE TABLE, CREATE VOLUME
  ON SCHEMA __CATALOG__.bronze TO `data-engineers`;
GRANT USE SCHEMA, SELECT, MODIFY, CREATE TABLE, CREATE VOLUME
  ON SCHEMA __CATALOG__.silver TO `data-engineers`;
GRANT USE SCHEMA, SELECT, MODIFY, CREATE TABLE, CREATE VOLUME
  ON SCHEMA __CATALOG__.gold TO `data-engineers`;

GRANT USE SCHEMA, SELECT ON SCHEMA __CATALOG__.silver TO `data-scientists`;
GRANT USE SCHEMA, SELECT ON SCHEMA __CATALOG__.gold TO `data-scientists`, `data-analysts`;

-- Pipelines read landing files and write checkpoints through the external locations.
GRANT READ FILES ON EXTERNAL LOCATION retail360_landing TO `data-engineers`;
GRANT READ FILES, WRITE FILES ON EXTERNAL LOCATION retail360_checkpoints TO `data-engineers`;
