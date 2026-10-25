"""Runtime configuration resolved from CLI arguments and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Names and locations for one deployment environment (dev, test or prod).

    All objects live in Unity Catalog under ``<catalog>.<layer>.<table>``; raw files are read
    from the ADLS Gen2 landing container through an external location.
    """

    catalog: str
    landing_root: str
    checkpoint_root: str
    bronze_schema: str = "bronze"
    silver_schema: str = "silver"
    gold_schema: str = "gold"
    quarantine_schema: str = "quarantine"

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from ``RETAIL360_*`` environment variables (set by the job)."""
        return cls(
            catalog=os.environ.get("RETAIL360_CATALOG", "retail360_dev"),
            landing_root=os.environ.get("RETAIL360_LANDING_ROOT", "").rstrip("/"),
            checkpoint_root=os.environ.get("RETAIL360_CHECKPOINT_ROOT", "").rstrip("/"),
        )

    def table(self, layer: str, name: str) -> str:
        """Fully qualified three-level table name."""
        schema = {
            "bronze": self.bronze_schema,
            "silver": self.silver_schema,
            "gold": self.gold_schema,
            "quarantine": self.quarantine_schema,
        }[layer]
        return f"{self.catalog}.{schema}.{name}"

    def landing_path(self, source: str, entity: str) -> str:
        """Landing folder for one entity, e.g. ``<root>/erp/orders``."""
        return f"{self.landing_root}/{source}/{entity}"

    def checkpoint_path(self, layer: str, entity: str) -> str:
        return f"{self.checkpoint_root}/{layer}/{entity}"
