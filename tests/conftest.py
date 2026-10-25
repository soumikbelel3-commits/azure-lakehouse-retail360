from __future__ import annotations

from pathlib import Path

import pytest
from pyspark.sql import DataFrame, SparkSession

from retail360.bronze import read_files_batch

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample"


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    session = (
        SparkSession.builder.master("local[2]")
        .appName("retail360-tests")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture(scope="session")
def raw(spark: SparkSession):
    """Callable returning the raw (all-string) sample frame for an entity."""
    folders = {
        "customers": "erp/customers",
        "products": "erp/products",
        "stores": "erp/stores",
        "orders": "erp/orders",
        "order_items": "erp/order_items",
        "pos_events": "streaming/pos_events",
    }

    def _load(entity: str) -> DataFrame:
        return read_files_batch(spark, entity, str(SAMPLE / folders[entity]))

    return _load
