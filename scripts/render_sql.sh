#!/usr/bin/env bash
# Substitute environment placeholders in the SQL setup scripts and print the result.
#   scripts/render_sql.sh sql/01_unity_catalog_foundation.sql retail360_dev stretail360dev1a2b \
#     | databricks sql query ... (or paste into a SQL warehouse)
set -euo pipefail
if [ "$#" -ne 3 ]; then
  echo "usage: $0 <sql-file> <catalog> <storage-account>" >&2
  exit 2
fi
sed -e "s/__CATALOG__/$2/g" -e "s/__STORAGE_ACCOUNT__/$3/g" "$1"
