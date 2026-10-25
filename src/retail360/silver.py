"""Silver layer: typed, standardised, de-duplicated, PII-minimised and quality-checked data."""

from __future__ import annotations

from collections.abc import Callable

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F

from retail360 import quality
from retail360.bronze import META_COLUMNS

EMAIL_REGEX = r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$"


# --------------------------------------------------------------------------------------
# Generic helpers
# --------------------------------------------------------------------------------------
def blank_to_null(col: str | Column) -> Column:
    """Trim a string column and turn empty strings into NULL."""
    c = F.trim(F.col(col) if isinstance(col, str) else col)
    return F.when(c == "", F.lit(None)).otherwise(c)


def try_cast(name: str, dtype: str) -> Column:
    """ANSI-safe cast: malformed values become NULL (and fail a rule) instead of failing the job."""
    return F.expr(f"try_cast(nullif(trim(`{name}`), '') AS {dtype})")


def to_ts(name: str) -> Column:
    """ANSI-safe timestamp parse."""
    return F.expr(f"try_to_timestamp(nullif(trim(`{name}`), ''))")


def to_dt(name: str) -> Column:
    """ANSI-safe date parse."""
    return F.expr(f"CAST(try_to_timestamp(nullif(trim(`{name}`), '')) AS DATE)")


def _meta(df: DataFrame) -> list[str]:
    """Lineage columns present on ``df`` that must survive a ``select``."""
    return [c for c in META_COLUMNS if c in df.columns]


def dedupe_latest(df: DataFrame, keys: list[str], order_col: str | None = None) -> DataFrame:
    """Keep one row per business key: the most recent by ``order_col`` (any row if ``None``)."""
    if order_col is None:
        return df.dropDuplicates(keys)
    window = Window.partitionBy(*keys).orderBy(F.col(order_col).desc_nulls_last())
    return df.withColumn("_rn", F.row_number().over(window)).where("_rn = 1").drop("_rn")


# --------------------------------------------------------------------------------------
# Cleaners: raw strings -> typed columns (no row is dropped here)
# --------------------------------------------------------------------------------------
def clean_customers(df: DataFrame) -> DataFrame:
    email = F.lower(blank_to_null("email"))
    phone_digits = F.regexp_replace(F.coalesce(F.col("phone"), F.lit("")), r"\D", "")
    return df.select(
        blank_to_null("customer_id").alias("customer_id"),
        F.initcap(blank_to_null("first_name")).alias("first_name"),
        F.initcap(blank_to_null("last_name")).alias("last_name"),
        # PII minimisation: keep a salted-by-column-mask hash and the domain, never the raw value.
        F.sha2(email, 256).alias("email_hash"),
        F.get(F.split(email, "@"), 1).alias("email_domain"),
        email.rlike(EMAIL_REGEX).alias("email_is_valid"),
        F.when(
            F.length(phone_digits) >= 4, F.concat(F.lit("***"), F.substring(phone_digits, -4, 4))
        ).alias("phone_masked"),
        F.year(to_dt("birth_date")).alias("birth_year"),
        F.upper(blank_to_null("country")).alias("country"),
        F.initcap(blank_to_null("city")).alias("city"),
        to_dt("signup_date").alias("signup_date"),
        F.upper(blank_to_null("loyalty_tier")).alias("loyalty_tier"),
        to_ts("updated_at").alias("updated_at"),
        *_meta(df),
    )


def clean_products(df: DataFrame) -> DataFrame:
    return df.select(
        blank_to_null("product_id").alias("product_id"),
        F.upper(blank_to_null("sku")).alias("sku"),
        blank_to_null("product_name").alias("product_name"),
        F.initcap(blank_to_null("category")).alias("category"),
        F.initcap(blank_to_null("subcategory")).alias("subcategory"),
        F.initcap(blank_to_null("brand")).alias("brand"),
        try_cast("unit_price", "decimal(10,2)").alias("unit_price"),
        try_cast("cost_price", "decimal(10,2)").alias("cost_price"),
        (F.upper(blank_to_null("active_flag")) == "Y").alias("is_active"),
        to_ts("updated_at").alias("updated_at"),
        *_meta(df),
    )


def clean_stores(df: DataFrame) -> DataFrame:
    return df.select(
        blank_to_null("store_id").alias("store_id"),
        blank_to_null("store_name").alias("store_name"),
        F.upper(blank_to_null("region")).alias("region"),
        F.upper(blank_to_null("country")).alias("country"),
        F.initcap(blank_to_null("city")).alias("city"),
        F.upper(blank_to_null("store_type")).alias("store_type"),
        to_dt("open_date").alias("open_date"),
        *_meta(df),
    )


def clean_orders(df: DataFrame) -> DataFrame:
    return df.select(
        blank_to_null("order_id").alias("order_id"),
        blank_to_null("customer_id").alias("customer_id"),
        blank_to_null("store_id").alias("store_id"),
        F.upper(blank_to_null("channel")).alias("channel"),
        to_ts("order_ts").alias("order_ts"),
        F.upper(blank_to_null("status")).alias("status"),
        F.upper(blank_to_null("currency")).alias("currency"),
        to_ts("updated_at").alias("updated_at"),
        *_meta(df),
    )


def clean_order_items(df: DataFrame) -> DataFrame:
    return df.select(
        blank_to_null("order_id").alias("order_id"),
        try_cast("line_no", "int").alias("line_no"),
        blank_to_null("product_id").alias("product_id"),
        try_cast("quantity", "int").alias("quantity"),
        try_cast("unit_price", "decimal(10,2)").alias("unit_price"),
        F.coalesce(try_cast("discount_pct", "decimal(5,2)"), F.lit(0).cast("decimal(5,2)")).alias(
            "discount_pct"
        ),
        *_meta(df),
    )


def clean_pos_events(df: DataFrame) -> DataFrame:
    return df.select(
        blank_to_null("event_id").alias("event_id"),
        blank_to_null("store_id").alias("store_id"),
        F.upper(blank_to_null("sku")).alias("sku"),
        F.upper(blank_to_null("event_type")).alias("event_type"),
        try_cast("quantity", "int").alias("quantity"),
        to_ts("event_ts").alias("event_ts"),
        *_meta(df),
    )


CLEANERS: dict[str, Callable[[DataFrame], DataFrame]] = {
    "customers": clean_customers,
    "products": clean_products,
    "stores": clean_stores,
    "orders": clean_orders,
    "order_items": clean_order_items,
    "pos_events": clean_pos_events,
}

# entity -> (business key, ordering column for "latest wins"; None keeps an arbitrary row)
DEDUPE_KEYS: dict[str, tuple[list[str], str | None]] = {
    "customers": (["customer_id"], "updated_at"),
    "products": (["product_id"], "updated_at"),
    "stores": (["store_id"], None),
    "orders": (["order_id"], "updated_at"),
    "order_items": (["order_id", "line_no"], None),
    "pos_events": (["event_id"], None),
}


def build_silver(entity: str, raw: DataFrame) -> tuple[DataFrame, DataFrame]:
    """Clean ``raw`` Bronze data and return ``(valid_deduplicated, quarantined)``.

    Rows failing any ``drop`` rule are quarantined with the list of failed rule names;
    survivors are de-duplicated on the entity's business key.
    """
    cleaned = CLEANERS[entity](raw)
    valid, invalid = quality.split_valid_invalid(cleaned, quality.RULES[entity]["drop"])
    keys, order_col = DEDUPE_KEYS[entity]
    return dedupe_latest(valid, keys, order_col), invalid
