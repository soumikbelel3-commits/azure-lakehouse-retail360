"""Delta Live Tables pipeline: Bronze -> Silver with expectations, SCD2 and quarantine.

Deployed by the Databricks Asset Bundle (``databricks/resources/pipelines.yml``). The cleaning
logic and the quality rules live in the ``retail360`` wheel so the exact same code is unit
tested locally and executed here.
"""

import dlt
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from retail360 import quality
from retail360.silver import CLEANERS, DEDUPE_KEYS

spark = SparkSession.getActiveSession()
CATALOG = spark.conf.get("retail360.catalog")
ENTITIES = ["customers", "products", "stores", "orders", "order_items", "pos_events"]


def _bronze(entity: str):
    return spark.readStream.table(f"{CATALOG}.bronze.{entity}")


def build_entity(entity: str) -> None:
    drop_rules = quality.RULES[entity]["drop"]
    warn_rules = quality.RULES[entity]["warn"]
    keys, order_col = DEDUPE_KEYS[entity]

    @dlt.view(name=f"{entity}_clean")
    @dlt.expect_all(warn_rules)
    @dlt.expect_all_or_drop(drop_rules)
    def _clean():
        return CLEANERS[entity](_bronze(entity))

    dlt.create_streaming_table(
        name=entity, comment=f"Silver {entity}: typed, de-duplicated, PII-minimised"
    )
    dlt.apply_changes(
        target=entity,
        source=f"{entity}_clean",
        keys=keys,
        sequence_by=F.col(order_col or "_ingested_at"),
        # Customer history (tier changes, relocations) is kept as slowly changing dimension type 2.
        stored_as_scd_type=2 if entity == "customers" else 1,
    )

    @dlt.table(name=f"{entity}_quarantine", comment=f"Rows rejected by {entity} quality rules")
    def _quarantine():
        _, invalid = quality.split_valid_invalid(CLEANERS[entity](_bronze(entity)), drop_rules)
        return invalid


for _entity in ENTITIES:
    build_entity(_entity)
