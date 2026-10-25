"""Job task: ingest landed files into Bronze Delta tables with Auto Loader.

Entry point name: ``retail360-bronze`` (see ``databricks/resources/jobs.yml``).
"""

from __future__ import annotations

import argparse
import uuid

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from retail360.bronze import (
    add_ingestion_metadata,
    read_autoloader,
    read_eventhubs_kafka,
    write_bronze_stream,
)
from retail360.config import Settings
from retail360.schemas import SOURCES


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Landing -> Bronze (Auto Loader)")
    p.add_argument("--catalog", required=True)
    p.add_argument(
        "--landing-root", required=True, help="abfss://landing@<account>.dfs.core.windows.net"
    )
    p.add_argument("--checkpoint-root", required=True)
    p.add_argument("--entities", nargs="*", default=list(SOURCES), help="Subset to ingest")
    p.add_argument("--continuous", action="store_true", help="Keep the POS stream running")
    p.add_argument("--batch-id", default=None)
    p.add_argument(
        "--pos-source",
        choices=["files", "eventhubs"],
        default="files",
        help="files: Auto Loader on landed JSON (dev/backfill); eventhubs: Kafka endpoint",
    )
    p.add_argument("--eventhubs-namespace", default=None)
    p.add_argument("--eventhub", default="pos-events")
    p.add_argument(
        "--secret-scope", default="retail360", help="Holds sp-tenant-id/-client-id/-secret"
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    spark = SparkSession.builder.getOrCreate()
    settings = Settings(
        catalog=args.catalog,
        landing_root=args.landing_root.rstrip("/"),
        checkpoint_root=args.checkpoint_root.rstrip("/"),
    )
    batch_id = args.batch_id or uuid.uuid4().hex
    queries = []
    for entity in args.entities:
        source, _, _ = SOURCES[entity]
        if entity == "pos_events" and args.pos_source == "eventhubs":
            from pyspark.dbutils import DBUtils  # only available on Databricks

            secrets = DBUtils(spark).secrets
            raw = read_eventhubs_kafka(
                spark,
                entity,
                args.eventhubs_namespace,
                args.eventhub,
                secrets.get(args.secret_scope, "sp-tenant-id"),
                secrets.get(args.secret_scope, "sp-client-id"),
                secrets.get(args.secret_scope, "sp-client-secret"),
            )
            df = add_ingestion_metadata(raw, batch_id, F.col("_kafka_ref"))
        else:
            raw = read_autoloader(
                spark,
                entity,
                settings.landing_path(source, entity),
                settings.checkpoint_path("schemas", entity),
            )
            df = add_ingestion_metadata(raw, batch_id, F.col("_metadata.file_path"))
        continuous = args.continuous and SOURCES[entity][1] == "json"
        queries.append(
            write_bronze_stream(
                df,
                settings.table("bronze", entity),
                settings.checkpoint_path("bronze", entity),
                continuous=continuous,
            )
        )
    for q in queries:
        q.awaitTermination()


if __name__ == "__main__":
    main()
