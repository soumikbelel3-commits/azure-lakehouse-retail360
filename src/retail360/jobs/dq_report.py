"""Job task: measure source data quality on Bronze and fail the run when it degrades.

Entry point name: ``retail360-dq``. Results are appended to ``<catalog>.gold.dq_results`` so
they can be charted in Power BI and alerted on from Azure Monitor.
"""

from __future__ import annotations

import argparse
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from retail360 import quality
from retail360.config import Settings
from retail360.schemas import SOURCES
from retail360.silver import CLEANERS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bronze data quality report")
    p.add_argument("--catalog", required=True)
    p.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.95,
        help="Fail when any drop-rule pass rate is lower",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    spark = SparkSession.builder.getOrCreate()
    s = Settings(catalog=args.catalog, landing_root="", checkpoint_root="")

    rows, breaches = [], []
    for entity in SOURCES:
        cleaned = CLEANERS[entity](spark.table(s.table("bronze", entity)))
        rates = quality.evaluate_entity(cleaned, entity)
        for rule, rate in rates.items():
            kind = "drop" if rule in quality.RULES[entity]["drop"] else "warn"
            rows.append((entity, rule, kind, rate))
            if kind == "drop" and rate < args.min_pass_rate:
                breaches.append(f"{entity}.{rule}={rate:.3f}")

    result = spark.createDataFrame(
        rows, "entity string, rule string, kind string, pass_rate double"
    )
    result = result.withColumn("run_ts", F.current_timestamp())
    result.write.format("delta").mode("append").saveAsTable(s.table("gold", "dq_results"))

    if breaches:
        print(
            f"Data quality below {args.min_pass_rate:.0%}: {', '.join(breaches)}", file=sys.stderr
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
