"""Job task: build the Gold star schema and aggregates from Silver.

Entry point name: ``retail360-gold``.
"""

from __future__ import annotations

import argparse
from datetime import date

from pyspark.sql import SparkSession

from retail360 import gold
from retail360.config import Settings
from retail360.io import merge_table, overwrite_table


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Silver -> Gold")
    p.add_argument("--catalog", required=True)
    p.add_argument("--date-start", default="2024-01-01")
    p.add_argument("--date-end", default="2030-12-31")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    spark = SparkSession.builder.getOrCreate()
    s = Settings(catalog=args.catalog, landing_root="", checkpoint_root="")

    # Customers are an SCD2 table in Silver; Gold dimensions expose the current version only.
    customers = spark.table(s.table("silver", "customers")).where("__END_AT IS NULL")
    products = spark.table(s.table("silver", "products"))
    stores = spark.table(s.table("silver", "stores"))
    orders = spark.table(s.table("silver", "orders"))
    items = spark.table(s.table("silver", "order_items"))
    pos = spark.table(s.table("silver", "pos_events"))

    dim_customer = gold.build_dim_customer(customers)
    dim_product = gold.build_dim_product(products)
    dim_store = gold.build_dim_store(stores)
    dim_date = gold.build_dim_date(
        spark, date.fromisoformat(args.date_start), date.fromisoformat(args.date_end)
    )
    fact_sales = gold.build_fact_sales(orders, items, dim_customer, dim_product, dim_store)

    overwrite_table(dim_customer, s.table("gold", "dim_customer"))
    overwrite_table(dim_product, s.table("gold", "dim_product"))
    overwrite_table(dim_store, s.table("gold", "dim_store"))
    overwrite_table(dim_date, s.table("gold", "dim_date"))
    merge_table(spark, fact_sales, s.table("gold", "fact_sales"), ["order_id", "line_no"])
    overwrite_table(
        gold.build_agg_daily_sales(spark.table(s.table("gold", "fact_sales")), dim_product),
        s.table("gold", "agg_daily_sales"),
    )
    overwrite_table(gold.build_agg_hourly_pos(pos), s.table("gold", "agg_hourly_pos"))


if __name__ == "__main__":
    main()
