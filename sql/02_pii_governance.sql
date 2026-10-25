-- Column masking and tagging. Run after the first successful pipeline run, once the Silver and
-- Gold tables exist. Placeholders are substituted by scripts/render_sql.sh.
--
-- Clear-text contact data never reaches Silver (emails are hashed, phones are masked). Names are
-- the remaining direct identifiers, so they are masked for everyone outside `pii-readers`.

CREATE OR REPLACE FUNCTION __CATALOG__.gold.mask_pii_text(value STRING)
  RETURN CASE WHEN is_account_group_member('pii-readers') THEN value ELSE '***' END;

ALTER TABLE __CATALOG__.gold.dim_customer ALTER COLUMN first_name SET MASK __CATALOG__.gold.mask_pii_text;
ALTER TABLE __CATALOG__.gold.dim_customer ALTER COLUMN last_name  SET MASK __CATALOG__.gold.mask_pii_text;
ALTER TABLE __CATALOG__.silver.customers  ALTER COLUMN first_name SET MASK __CATALOG__.gold.mask_pii_text;
ALTER TABLE __CATALOG__.silver.customers  ALTER COLUMN last_name  SET MASK __CATALOG__.gold.mask_pii_text;

-- Discoverability: tag sensitive columns so Purview and the catalog explorer can surface them.
ALTER TABLE __CATALOG__.gold.dim_customer ALTER COLUMN first_name    SET TAGS ('classification' = 'pii');
ALTER TABLE __CATALOG__.gold.dim_customer ALTER COLUMN last_name     SET TAGS ('classification' = 'pii');
ALTER TABLE __CATALOG__.gold.dim_customer ALTER COLUMN email_hash    SET TAGS ('classification' = 'pseudonymised');
ALTER TABLE __CATALOG__.gold.dim_customer ALTER COLUMN phone_masked  SET TAGS ('classification' = 'pseudonymised');

-- Table documentation shown in the catalog and picked up by BI tools.
COMMENT ON TABLE __CATALOG__.gold.fact_sales IS 'One row per order line for completed orders; grain: order_id + line_no';
COMMENT ON TABLE __CATALOG__.gold.agg_daily_sales IS 'Daily net sales, units and margin by store and product category';
COMMENT ON TABLE __CATALOG__.gold.agg_hourly_pos IS 'Hourly in-store POS activity from the streaming path';
