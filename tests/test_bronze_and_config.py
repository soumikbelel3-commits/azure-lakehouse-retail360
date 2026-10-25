from __future__ import annotations

from pyspark.sql import functions as F

from retail360.bronze import META_COLUMNS, add_ingestion_metadata
from retail360.config import Settings
from retail360.schemas import BATCH_ENTITIES, SOURCES, STREAM_ENTITIES, raw_schema


def test_raw_schemas_are_all_strings_and_match_the_sample_files(raw):
    for entity in SOURCES:
        schema = raw_schema(entity)
        assert all(f.dataType.simpleString() == "string" for f in schema.fields)
        assert raw(entity).columns == [f.name for f in schema.fields]
        assert raw(entity).count() > 0


def test_entities_are_partitioned_into_batch_and_stream():
    assert set(BATCH_ENTITIES) | set(STREAM_ENTITIES) == set(SOURCES)
    assert STREAM_ENTITIES == ["pos_events"]


def test_ingestion_metadata_adds_lineage_columns(spark):
    df = spark.createDataFrame([("a",)], "v string")
    out = add_ingestion_metadata(df, "batch-1", F.lit("abfss://landing/x.csv"))
    assert set(META_COLUMNS) <= set(out.columns)
    row = out.first()
    assert row._batch_id == "batch-1"
    assert row._source_file == "abfss://landing/x.csv"
    assert row._ingested_at is not None


def test_metadata_survives_silver_cleaning(spark):
    from retail360.silver import build_silver

    raw_df = spark.createDataFrame(
        [("S1", "Store", "emea", "de", "berlin", "flagship", "2020-01-01")],
        "store_id string, store_name string, region string, country string, city string, "
        "store_type string, open_date string",
    )
    valid, _ = build_silver("stores", add_ingestion_metadata(raw_df, "b1", F.lit("f.csv")))
    row = valid.first()
    assert (row._batch_id, row._source_file) == ("b1", "f.csv")
    assert (row.region, row.country, row.city) == ("EMEA", "DE", "Berlin")


def test_settings_build_three_level_names_and_paths():
    s = Settings(
        catalog="retail360_dev",
        landing_root="abfss://landing@acct.dfs.core.windows.net",
        checkpoint_root="abfss://checkpoints@acct.dfs.core.windows.net",
    )
    assert s.table("bronze", "orders") == "retail360_dev.bronze.orders"
    assert s.table("gold", "fact_sales") == "retail360_dev.gold.fact_sales"
    assert s.landing_path("erp", "orders").endswith("/erp/orders")
    assert s.checkpoint_path("bronze", "orders").endswith("/bronze/orders")


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("RETAIL360_CATALOG", "retail360_prod")
    monkeypatch.setenv("RETAIL360_LANDING_ROOT", "abfss://l@a.dfs.core.windows.net/")
    monkeypatch.setenv("RETAIL360_CHECKPOINT_ROOT", "abfss://c@a.dfs.core.windows.net/")
    s = Settings.from_env()
    assert s.catalog == "retail360_prod"
    assert not s.landing_root.endswith("/")
