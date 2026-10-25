from __future__ import annotations

from pyspark.sql import functions as F

from retail360 import quality
from retail360.silver import blank_to_null, build_silver, dedupe_latest


def test_blank_to_null_trims_and_nulls_empty(spark):
    df = spark.createDataFrame([(" a ",), ("   ",), ("",), (None,)], "v string")
    out = [r.v for r in df.select(blank_to_null("v").alias("v")).collect()]
    assert out == ["a", None, None, None]


def test_dedupe_latest_keeps_most_recent_version(spark):
    df = spark.createDataFrame(
        [("k1", "old", 1), ("k1", "new", 2), ("k2", "only", 1)], "key string, val string, ts int"
    )
    out = {r.key: r.val for r in dedupe_latest(df, ["key"], "ts").collect()}
    assert out == {"k1": "new", "k2": "only"}


def test_customers_are_deduplicated_quarantined_and_pii_minimised(raw):
    valid, invalid = build_silver("customers", raw("customers"))

    assert valid.count() == 60
    assert valid.select("customer_id").distinct().count() == 60
    assert invalid.count() == 2  # blank and null customer_id
    assert all(r._dq_failed_rules == ["customer_id_present"] for r in invalid.collect())

    # clear-text PII must not survive into Silver
    assert "email" not in valid.columns and "phone" not in valid.columns
    row = valid.where("customer_id = 'C00001'").first()
    assert len(row.email_hash) == 64
    assert row.phone_masked.startswith("***") and len(row.phone_masked) == 7
    assert row.email_domain == "example.com"


def test_latest_customer_version_wins(raw):
    valid, _ = build_silver("customers", raw("customers"))
    # the generator appends stale copies (updated_at in mid-2025) of C00004, C00008, C00012,
    # C00020 and C00024; the newer 2026 record of each must be the survivor
    stale_ids = ["C00004", "C00008", "C00012", "C00020", "C00024"]
    survivors = valid.where(F.col("customer_id").isin(stale_ids))
    assert survivors.count() == 5
    assert survivors.where("updated_at < timestamp'2026-01-01'").count() == 0
    assert valid.where("updated_at < timestamp'2026-01-01'").count() == 0


def test_invalid_emails_are_flagged_but_kept(raw):
    valid, _ = build_silver("customers", raw("customers"))
    assert valid.where("NOT email_is_valid").count() == 3
    rates = quality.evaluate_entity(valid, "customers")
    assert rates["email_format_valid"] == 57 / 60


def test_orders_exact_duplicates_and_null_customers(raw):
    valid, invalid = build_silver("orders", raw("orders"))
    assert valid.count() == 240
    assert valid.select("order_id").distinct().count() == 240
    assert invalid.count() == 1
    assert invalid.first()._dq_failed_rules == ["customer_id_present"]
    assert valid.where("order_ts IS NULL").count() == 0


def test_non_positive_quantities_are_quarantined(raw):
    valid, invalid = build_silver("order_items", raw("order_items"))
    assert invalid.count() == 3
    assert all("quantity_positive" in r._dq_failed_rules for r in invalid.collect())
    assert valid.where("quantity <= 0").count() == 0
    assert valid.count() == 727


def test_products_stale_duplicate_is_removed_and_types_are_applied(raw):
    valid, _ = build_silver("products", raw("products"))
    assert valid.count() == 27
    assert dict(valid.dtypes)["unit_price"] == "decimal(10,2)"
    assert dict(valid.dtypes)["is_active"] == "boolean"


def test_pos_events_at_least_once_duplicates_are_collapsed(raw):
    valid, invalid = build_silver("pos_events", raw("pos_events"))
    assert valid.count() == 400
    assert invalid.count() == 0
    assert dict(valid.dtypes)["event_ts"] == "timestamp"


def test_malformed_values_do_not_fail_the_job(spark):
    """ANSI mode must not raise on garbage: bad numbers become NULL and are quarantined."""
    bad = spark.createDataFrame(
        [("O1", "1", "P1", "abc", "9.99", "0"), ("O2", "1", "P1", "2", "9.99", "0")],
        "order_id string, line_no string, product_id string, quantity string, unit_price string, "
        "discount_pct string",
    )
    valid, invalid = build_silver("order_items", bad)
    assert valid.count() == 1 and invalid.count() == 1
    assert invalid.first().order_id == "O1"


def test_split_with_no_rules_returns_everything_valid(spark):
    df = spark.createDataFrame([(1,), (2,)], "x int")
    valid, invalid = quality.split_valid_invalid(df, {})
    assert valid.count() == 2 and invalid.count() == 0
