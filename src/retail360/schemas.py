"""Source contracts: column lists per entity and where each entity comes from.

Bronze keeps every source column as a string (schema-on-read safety). Typing happens in Silver.
"""

from __future__ import annotations

from pyspark.sql import types as T

# entity -> (source system folder, file format, ordered columns)
SOURCES: dict[str, tuple[str, str, list[str]]] = {
    "customers": (
        "erp",
        "csv",
        [
            "customer_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "birth_date",
            "country",
            "city",
            "signup_date",
            "loyalty_tier",
            "updated_at",
        ],
    ),
    "products": (
        "erp",
        "csv",
        [
            "product_id",
            "sku",
            "product_name",
            "category",
            "subcategory",
            "brand",
            "unit_price",
            "cost_price",
            "active_flag",
            "updated_at",
        ],
    ),
    "stores": (
        "erp",
        "csv",
        ["store_id", "store_name", "region", "country", "city", "store_type", "open_date"],
    ),
    "orders": (
        "erp",
        "csv",
        [
            "order_id",
            "customer_id",
            "store_id",
            "channel",
            "order_ts",
            "status",
            "currency",
            "updated_at",
        ],
    ),
    "order_items": (
        "erp",
        "csv",
        ["order_id", "line_no", "product_id", "quantity", "unit_price", "discount_pct"],
    ),
    "pos_events": (
        "streaming",
        "json",
        ["event_id", "store_id", "sku", "event_type", "quantity", "event_ts"],
    ),
}

BATCH_ENTITIES = [name for name, (_, fmt, _) in SOURCES.items() if fmt == "csv"]
STREAM_ENTITIES = [name for name, (_, fmt, _) in SOURCES.items() if fmt == "json"]


def raw_schema(entity: str) -> T.StructType:
    """All-string schema used when reading the raw files for ``entity``."""
    _, _, columns = SOURCES[entity]
    return T.StructType([T.StructField(c, T.StringType(), True) for c in columns])
