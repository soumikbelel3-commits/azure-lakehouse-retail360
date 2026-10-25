"""Validate every JSON and YAML file in the repository parses, and check ADF cross-references.

Run in CI and via ``make validate``. Exits non-zero on the first class of failure found.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "node_modules", "spark-warehouse", ".terraform", "metastore_db"}


def iter_files(*suffixes: str):
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in suffixes and not (SKIP_DIRS & set(path.parts)):
            yield path


def check_parse() -> list[str]:
    errors = []
    for path in iter_files(".json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    for path in iter_files(".yml", ".yaml"):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    return errors


def check_adf_references() -> list[str]:
    """Every dataset, linked service and pipeline referenced in adf/ must be defined there."""
    adf = ROOT / "adf"
    defined: dict[str, set[str]] = {"LinkedService": set(), "Dataset": set(), "Pipeline": set()}
    kinds = {"linkedService": "LinkedService", "dataset": "Dataset", "pipeline": "Pipeline"}
    docs = []
    for folder, kind in kinds.items():
        for path in (adf / folder).glob("*.json"):
            doc = json.loads(path.read_text(encoding="utf-8"))
            defined[kind].add(doc["name"])
            docs.append((path, doc))
    for path in (adf / "trigger").glob("*.json"):
        docs.append((path, json.loads(path.read_text(encoding="utf-8"))))

    errors: list[str] = []

    def walk(node, path):
        if isinstance(node, dict):
            ref, typ = node.get("referenceName"), node.get("type", "")
            if ref and typ.endswith("Reference"):
                kind = typ.replace("Reference", "")
                # Integration runtimes are created by Terraform, not stored in adf/.
                if kind in defined and ref not in defined[kind]:
                    errors.append(f"{path.relative_to(ROOT)}: undefined {kind} '{ref}'")
            for value in node.values():
                walk(value, path)
        elif isinstance(node, list):
            for value in node:
                walk(value, path)

    for path, doc in docs:
        walk(doc, path)
    return errors


def main() -> int:
    errors = check_parse() + check_adf_references()
    for line in errors:
        print(f"ERROR {line}", file=sys.stderr)
    if not errors:
        print("All JSON/YAML files parse and ADF references resolve.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
