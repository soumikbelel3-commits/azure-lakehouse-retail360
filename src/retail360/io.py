"""Delta write helpers used by the Gold and data-quality jobs (Databricks runtime)."""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession


def overwrite_table(df: DataFrame, table: str) -> None:
    """Atomically replace a table (dimensions and small aggregates)."""
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(table)


def merge_table(spark: SparkSession, df: DataFrame, table: str, keys: list[str]) -> None:
    """Idempotent upsert on ``keys``; creates the table on first run."""
    if not spark.catalog.tableExists(table):
        df.write.format("delta").saveAsTable(table)
        return
    from delta.tables import DeltaTable  # available on the Databricks runtime

    condition = " AND ".join(f"t.{k} <=> s.{k}" for k in keys)
    (
        DeltaTable.forName(spark, table)
        .alias("t")
        .merge(df.alias("s"), condition)
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
