"""Bronze layer helpers: append-only, schema-on-read, with lineage columns."""

from __future__ import annotations

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F

from retail360.schemas import SOURCES, raw_schema

META_COLUMNS = ("_ingested_at", "_source_file", "_batch_id")


def add_ingestion_metadata(
    df: DataFrame, batch_id: str, source_file: Column | None = None
) -> DataFrame:
    """Append lineage columns so every Bronze row can be traced back to its file and run."""
    return (
        df.withColumn("_ingested_at", F.current_timestamp())
        .withColumn(
            "_source_file", source_file if source_file is not None else F.lit(None).cast("string")
        )
        .withColumn("_batch_id", F.lit(batch_id))
    )


def read_autoloader(spark: SparkSession, entity: str, path: str, schema_location: str) -> DataFrame:
    """Incrementally discover new files with Databricks Auto Loader (``cloudFiles``).

    Runs on Databricks only. The explicit all-string schema keeps ingestion resilient to
    source drift; unexpected columns are rescued into ``_rescued_data`` instead of failing.
    """
    _, fmt, _ = SOURCES[entity]
    reader = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", fmt)
        .option("cloudFiles.schemaLocation", schema_location)
        .option("cloudFiles.schemaEvolutionMode", "rescue")
        .schema(raw_schema(entity))
    )
    if fmt == "csv":
        reader = reader.option("header", "true").option("multiLine", "false")
    return reader.load(path)


def read_eventhubs_kafka(
    spark: SparkSession,
    entity: str,
    namespace: str,
    event_hub: str,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    consumer_group: str = "databricks",
) -> DataFrame:
    """Read a JSON event stream from Event Hubs through its Kafka endpoint (port 9093).

    Authenticates with a Microsoft Entra service principal (OAUTHBEARER) because local SAS
    keys are disabled on the namespace. Runs on Databricks only; the payload is parsed with the
    same all-string schema as the file-based path so Silver does not care where it came from.
    """
    login = (
        "kafkashaded.org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required "
        f'clientId="{client_id}" clientSecret="{client_secret}" '
        'scope="https://eventhubs.azure.net/.default" '
        f'ssl.protocol="SSL";'
    )
    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", f"{namespace}.servicebus.windows.net:9093")
        .option("subscribe", event_hub)
        .option("kafka.group.id", consumer_group)
        .option("kafka.security.protocol", "SASL_SSL")
        .option("kafka.sasl.mechanism", "OAUTHBEARER")
        .option("kafka.sasl.jaas.config", login)
        .option(
            "kafka.sasl.oauthbearer.token.endpoint.url",
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        )
        .option(
            "kafka.sasl.login.callback.handler.class",
            "kafkashaded.org.apache.kafka.common.security.oauthbearer.secured."
            "OAuthBearerLoginCallbackHandler",
        )
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .load()
    )
    parsed = raw.select(
        F.from_json(F.col("value").cast("string"), raw_schema(entity)).alias("p"),
        F.col("topic"),
        F.col("partition"),
        F.col("offset"),
    )
    return parsed.select(
        "p.*", F.concat_ws("/", "topic", "partition", "offset").alias("_kafka_ref")
    )


def read_files_batch(spark: SparkSession, entity: str, path: str) -> DataFrame:
    """Plain batch read of the same files (local development and unit tests)."""
    _, fmt, _ = SOURCES[entity]
    reader = spark.read.schema(raw_schema(entity))
    if fmt == "csv":
        return reader.option("header", "true").csv(path)
    return reader.json(path)


def write_bronze_stream(df: DataFrame, table: str, checkpoint: str, continuous: bool = False):
    """Append a streaming frame to a Delta table.

    By default uses ``availableNow`` so the job processes the backlog and stops, which keeps
    cost low; set ``continuous`` for sub-minute latency on the POS stream.
    """
    writer = (
        df.writeStream.format("delta").option("checkpointLocation", checkpoint).outputMode("append")
    )
    writer = (
        writer.trigger(processingTime="10 seconds")
        if continuous
        else writer.trigger(availableNow=True)
    )
    return writer.toTable(table)
