from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from retail360 import gold
from retail360.silver import build_silver


@pytest.fixture(scope="module")
def silver(raw):
    return {
        e: build_silver(e, raw(e))[0]
        for e in ("customers", "products", "stores", "orders", "order_items", "pos_events")
    }


@pytest.fixture(scope="module")
def dims(silver):
    return (
        gold.build_dim_customer(silver["customers"], as_of=date(2026, 10, 1)),
        gold.build_dim_product(silver["products"]),
        gold.build_dim_store(silver["stores"]),
    )


def test_dimension_surrogate_keys_are_unique_and_stable(dims):
    for dim, key in zip(dims, ("customer_key", "product_key", "store_key"), strict=True):
        assert dim.select(key).distinct().count() == dim.count()
    again = gold.build_dim_store(
        dims[2].select(
            "store_id", "store_name", "region", "country", "city", "store_type", "open_date"
        )
    )
    assert {r.store_key for r in again.collect()} == {r.store_key for r in dims[2].collect()}


def test_dim_customer_exposes_no_clear_text_pii(dims):
    cols = set(dims[0].columns)
    assert not {"email", "phone", "birth_date"} & cols
    assert {"email_hash", "phone_masked", "age_band"} <= cols


def test_age_band_uses_reference_year(spark):
    df = spark.createDataFrame(
        [("c1", 2010), ("c2", 2000), ("c3", 1985), ("c4", 1950), ("c5", None)],
        "customer_id string, birth_year int",
    ).selectExpr(
        "customer_id",
        "birth_year",
        "'a' first_name",
        "'b' last_name",
        "'h' email_hash",
        "'d' email_domain",
        "'p' phone_masked",
        "'DE' country",
        "'x' city",
        "'GOLD' loyalty_tier",
        "current_date() signup_date",
    )
    bands = {
        r.customer_id: r.age_band
        for r in gold.build_dim_customer(df, as_of=date(2026, 1, 1)).collect()
    }
    assert bands == {"c1": "18-24", "c2": "25-34", "c3": "35-49", "c4": "50+", "c5": "unknown"}


def test_dim_date_covers_range_without_gaps(spark):
    dim = gold.build_dim_date(spark, date(2026, 9, 1), date(2026, 9, 30))
    assert dim.count() == 30
    assert dim.where("date_key = 20260905").first().is_weekend is True  # Saturday
    assert dim.agg({"date_key": "min"}).first()[0] == 20260901


def test_fact_sales_only_contains_completed_orders_with_resolved_keys(silver, dims):
    fact = gold.build_fact_sales(silver["orders"], silver["order_items"], *dims)
    completed = silver["orders"].where("status = 'COMPLETED'").select("order_id")
    assert fact.join(completed, "order_id", "left_anti").count() == 0
    assert (
        fact.where("customer_key IS NULL OR product_key IS NULL OR store_key IS NULL").count() == 0
    )
    assert fact.select("order_id", "line_no").distinct().count() == fact.count()


def test_fact_sales_amount_arithmetic(spark, dims):
    orders = spark.createDataFrame(
        [("O1", "C00001", "S001", "ONLINE", "2026-09-10 10:00:00", "COMPLETED", "EUR")],
        "order_id string, customer_id string, store_id string, channel string, order_ts string, "
        "status string, currency string",
    ).selectExpr(
        "order_id",
        "customer_id",
        "store_id",
        "channel",
        "CAST(order_ts AS timestamp) order_ts",
        "status",
        "currency",
    )
    product = dims[1].first()
    items = spark.createDataFrame(
        [("O1", 1, product.product_id, 4, Decimal("50.00"), Decimal("10.00"))],
        "order_id string, line_no int, product_id string, quantity int, unit_price decimal(10,2), "
        "discount_pct decimal(5,2)",
    )
    row = gold.build_fact_sales(orders, items, *dims).first()
    assert row.gross_amount == Decimal("200.00")
    assert row.discount_amount == Decimal("20.00")
    assert row.net_amount == Decimal("180.00")
    expected_margin = Decimal("180.00") - 4 * product.cost_price
    assert row.margin_amount == expected_margin
    assert row.date_key == 20260910


def test_daily_aggregate_reconciles_to_fact(silver, dims):
    fact = gold.build_fact_sales(silver["orders"], silver["order_items"], *dims)
    agg = gold.build_agg_daily_sales(fact, dims[1])
    total_fact = fact.agg({"net_amount": "sum"}).first()[0]
    total_agg = agg.agg({"net_revenue": "sum"}).first()[0]
    assert total_fact == total_agg
    assert agg.agg({"units_sold": "sum"}).first()[0] == fact.agg({"quantity": "sum"}).first()[0]


def test_hourly_pos_nets_returns(silver):
    hourly = gold.build_agg_hourly_pos(silver["pos_events"])
    totals = hourly.agg({"units_sold": "sum", "units_returned": "sum", "net_units": "sum"}).first()
    assert totals["sum(net_units)"] == totals["sum(units_sold)"] - totals["sum(units_returned)"]
    assert hourly.agg({"events": "sum"}).first()[0] == 400
