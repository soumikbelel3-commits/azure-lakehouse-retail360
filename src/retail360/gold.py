"""Gold layer: conformed dimensions, the sales fact and business aggregates (star schema)."""

from __future__ import annotations

from datetime import date

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


def _key(*cols: str):
    """Deterministic 64-bit surrogate key derived from the business key."""
    return F.xxhash64(*[F.col(c) for c in cols])


def build_dim_customer(customers: DataFrame, as_of: date | None = None) -> DataFrame:
    year = F.lit(as_of.year) if as_of else F.year(F.current_date())
    age = year - F.col("birth_year")
    return customers.select(
        _key("customer_id").alias("customer_key"),
        "customer_id",
        "first_name",
        "last_name",
        "email_hash",
        "email_domain",
        "phone_masked",
        "country",
        "city",
        "loyalty_tier",
        "signup_date",
        F.when(age < 25, "18-24")
        .when(age < 35, "25-34")
        .when(age < 50, "35-49")
        .when(age.isNotNull(), "50+")
        .otherwise("unknown")
        .alias("age_band"),
    )


def build_dim_product(products: DataFrame) -> DataFrame:
    margin = F.when(
        F.col("unit_price") > 0, (F.col("unit_price") - F.col("cost_price")) / F.col("unit_price")
    )
    return products.select(
        _key("product_id").alias("product_key"),
        "product_id",
        "sku",
        "product_name",
        "category",
        "subcategory",
        "brand",
        "unit_price",
        "cost_price",
        F.round(margin, 4).alias("margin_pct"),
        "is_active",
    )


def build_dim_store(stores: DataFrame) -> DataFrame:
    return stores.select(
        _key("store_id").alias("store_key"),
        "store_id",
        "store_name",
        "region",
        "country",
        "city",
        "store_type",
        "open_date",
    )


def build_dim_date(spark: SparkSession, start: date, end: date) -> DataFrame:
    days = spark.sql(
        f"SELECT explode(sequence(to_date('{start}'), to_date('{end}'), interval 1 day)) AS date"
    )
    return days.select(
        F.date_format("date", "yyyyMMdd").cast("int").alias("date_key"),
        "date",
        F.year("date").alias("year"),
        F.quarter("date").alias("quarter"),
        F.month("date").alias("month"),
        F.date_format("date", "MMMM").alias("month_name"),
        F.weekofyear("date").alias("week_of_year"),
        F.dayofweek("date").alias("day_of_week"),
        F.dayofweek("date").isin(1, 7).alias("is_weekend"),
    )


def build_fact_sales(
    orders: DataFrame,
    order_items: DataFrame,
    dim_customer: DataFrame,
    dim_product: DataFrame,
    dim_store: DataFrame,
) -> DataFrame:
    """One row per completed order line, keyed to the conformed dimensions."""
    completed = orders.where(F.col("status") == "COMPLETED").select(
        "order_id", "customer_id", "store_id", "channel", "order_ts", "currency"
    )
    lines = order_items.join(completed, "order_id", "inner")
    lines = (
        lines.join(
            dim_product.select("product_id", "product_key", "cost_price"), "product_id", "inner"
        )
        .join(dim_customer.select("customer_id", "customer_key"), "customer_id", "left")
        .join(dim_store.select("store_id", "store_key"), "store_id", "left")
    )
    gross = F.col("quantity") * F.col("unit_price")
    discount = gross * F.col("discount_pct") / F.lit(100)
    cost = F.col("quantity") * F.col("cost_price")
    return lines.select(
        "order_id",
        "line_no",
        F.date_format("order_ts", "yyyyMMdd").cast("int").alias("date_key"),
        "customer_key",
        "product_key",
        "store_key",
        "channel",
        "quantity",
        F.round(gross, 2).cast("decimal(14,2)").alias("gross_amount"),
        F.round(discount, 2).cast("decimal(14,2)").alias("discount_amount"),
        F.round(gross - discount, 2).cast("decimal(14,2)").alias("net_amount"),
        F.round(gross - discount - cost, 2).cast("decimal(14,2)").alias("margin_amount"),
        "currency",
        "order_ts",
    )


def build_agg_daily_sales(fact_sales: DataFrame, dim_product: DataFrame) -> DataFrame:
    """Daily revenue, units, orders and margin by store and product category."""
    enriched = fact_sales.join(dim_product.select("product_key", "category"), "product_key", "left")
    return (
        enriched.groupBy("date_key", "store_key", "category")
        .agg(
            F.sum("net_amount").cast("decimal(16,2)").alias("net_revenue"),
            F.sum("margin_amount").cast("decimal(16,2)").alias("margin"),
            F.sum("quantity").alias("units_sold"),
            F.countDistinct("order_id").alias("orders"),
        )
        .withColumn(
            "avg_order_value",
            F.round(F.col("net_revenue") / F.col("orders"), 2).cast("decimal(14,2)"),
        )
    )


def build_agg_hourly_pos(pos_events: DataFrame) -> DataFrame:
    """Hourly in-store activity from the POS event stream (sales net of returns)."""
    sold = F.when(F.col("event_type") == "SALE", F.col("quantity")).otherwise(0)
    returned = F.when(F.col("event_type") == "RETURN", F.col("quantity")).otherwise(0)
    return (
        pos_events.groupBy("store_id", F.date_trunc("hour", "event_ts").alias("event_hour"))
        .agg(
            F.sum(sold).alias("units_sold"),
            F.sum(returned).alias("units_returned"),
            F.count("*").alias("events"),
        )
        .withColumn("net_units", F.col("units_sold") - F.col("units_returned"))
    )
