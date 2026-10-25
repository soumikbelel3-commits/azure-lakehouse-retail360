"""Data-quality rules shared by the Delta Live Tables pipeline, batch jobs and unit tests.

Each rule is a Spark SQL boolean expression that must be TRUE for a row to be acceptable.
``drop`` rules send failing rows to quarantine; ``warn`` rules only report pass rates.
The same dictionaries feed ``dlt.expect_all_or_drop`` / ``dlt.expect_all`` in production.
"""

from __future__ import annotations

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F

KNOWN_STATUSES = "('COMPLETED','CANCELLED','RETURNED')"
KNOWN_EVENTS = "('SALE','RETURN')"

RULES: dict[str, dict[str, dict[str, str]]] = {
    "customers": {
        "drop": {"customer_id_present": "customer_id IS NOT NULL"},
        "warn": {
            "email_format_valid": "email_is_valid",
            "signup_date_present": "signup_date IS NOT NULL",
        },
    },
    "products": {
        "drop": {
            "product_id_present": "product_id IS NOT NULL",
            "unit_price_non_negative": "unit_price IS NOT NULL AND unit_price >= 0",
        },
        "warn": {"price_covers_cost": "unit_price >= cost_price"},
    },
    "stores": {
        "drop": {"store_id_present": "store_id IS NOT NULL"},
        "warn": {"country_is_iso2": "length(country) = 2"},
    },
    "orders": {
        "drop": {
            "order_id_present": "order_id IS NOT NULL",
            "customer_id_present": "customer_id IS NOT NULL",
            "order_ts_present": "order_ts IS NOT NULL",
            "status_known": f"status IN {KNOWN_STATUSES}",
        },
        "warn": {"currency_is_iso3": "length(currency) = 3"},
    },
    "order_items": {
        "drop": {
            "order_id_present": "order_id IS NOT NULL",
            "product_id_present": "product_id IS NOT NULL",
            "quantity_positive": "quantity IS NOT NULL AND quantity > 0",
            "unit_price_non_negative": "unit_price IS NOT NULL AND unit_price >= 0",
        },
        "warn": {"discount_in_range": "discount_pct BETWEEN 0 AND 100"},
    },
    "pos_events": {
        "drop": {
            "event_id_present": "event_id IS NOT NULL",
            "store_id_present": "store_id IS NOT NULL",
            "event_type_known": f"event_type IN {KNOWN_EVENTS}",
            "quantity_positive": "quantity IS NOT NULL AND quantity > 0",
            "event_ts_present": "event_ts IS NOT NULL",
        },
        "warn": {},
    },
}


def _all_pass(rules: dict[str, str]) -> Column:
    """TRUE only when every rule evaluates to TRUE (NULL counts as a failure)."""
    cond = F.lit(True)
    for expr in rules.values():
        cond = cond & F.coalesce(F.expr(expr), F.lit(False))
    return cond


def split_valid_invalid(df: DataFrame, rules: dict[str, str]) -> tuple[DataFrame, DataFrame]:
    """Split ``df`` into rows passing all ``rules`` and quarantined rows.

    Quarantined rows get ``_dq_failed_rules`` (array of rule names) for triage.
    """
    if not rules:
        return df, df.limit(0).withColumn("_dq_failed_rules", F.array().cast("array<string>"))

    failed = F.array_compact(
        F.array(
            *[
                F.when(F.coalesce(F.expr(expr), F.lit(False)), F.lit(None)).otherwise(F.lit(name))
                for name, expr in rules.items()
            ]
        )
    )
    flagged = df.withColumn("_dq_failed_rules", failed)
    valid = flagged.where(F.size("_dq_failed_rules") == 0).drop("_dq_failed_rules")
    invalid = flagged.where(F.size("_dq_failed_rules") > 0)
    return valid, invalid


def pass_rates(df: DataFrame, rules: dict[str, str]) -> dict[str, float]:
    """Share of rows (0-1) passing each rule; an empty frame reports 1.0 for every rule."""
    if not rules:
        return {}
    aggs = [
        F.avg(F.coalesce(F.expr(expr), F.lit(False)).cast("int")).alias(name)
        for name, expr in rules.items()
    ]
    row = df.agg(*aggs).first()
    return {name: (1.0 if row[name] is None else float(row[name])) for name in rules}


def evaluate_entity(df: DataFrame, entity: str) -> dict[str, float]:
    """Pass rates for every drop and warn rule of ``entity``."""
    rules = {**RULES[entity]["drop"], **RULES[entity]["warn"]}
    return pass_rates(df, rules)
