#!/usr/bin/env bash
# Deploy the Data Factory definitions in adf/ with the Azure CLI (needs `az extension add -n datafactory`).
# Placeholders in the JSON are replaced from the environment, so one set of files serves every stage.
#
#   RESOURCE_GROUP=rg-retail360-dev-weu FACTORY=adf-retail360-dev-weu \
#   STORAGE_ACCOUNT_NAME=... KEY_VAULT_NAME=... ERP_SQL_HOST=... scripts/deploy_adf.sh
set -euo pipefail

: "${RESOURCE_GROUP:?}" "${FACTORY:?}" "${STORAGE_ACCOUNT_NAME:?}" "${KEY_VAULT_NAME:?}" "${ERP_SQL_HOST:?}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/adf"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

render() { # file -> stdout with placeholders substituted
  sed -e "s|__STORAGE_ACCOUNT_NAME__|${STORAGE_ACCOUNT_NAME}|g" \
      -e "s|__KEY_VAULT_NAME__|${KEY_VAULT_NAME}|g" \
      -e "s|__ERP_SQL_HOST__|${ERP_SQL_HOST}|g" "$1"
}

# properties-only JSON for `az datafactory <kind> create --properties`
props() { render "$1" | jq -c '.properties'; }

for f in "$ROOT"/linkedService/*.json; do
  name="$(jq -r .name "$f")"; echo "linked service  $name"
  az datafactory linked-service create -g "$RESOURCE_GROUP" --factory-name "$FACTORY" -n "$name" --properties "$(props "$f")" -o none
done
for f in "$ROOT"/dataset/*.json; do
  name="$(jq -r .name "$f")"; echo "dataset         $name"
  az datafactory dataset create -g "$RESOURCE_GROUP" --factory-name "$FACTORY" -n "$name" --properties "$(props "$f")" -o none
done
# Child pipeline first: PL_Master_Ingest references PL_Ingest_Entity.
for name in PL_Ingest_Entity PL_Master_Ingest; do
  echo "pipeline        $name"
  az datafactory pipeline create -g "$RESOURCE_GROUP" --factory-name "$FACTORY" -n "$name" \
    --pipeline "$(props "$ROOT/pipeline/$name.json")" -o none
done
# Triggers are created stopped; start them deliberately (`az datafactory trigger start`).
for f in "$ROOT"/trigger/*.json; do
  name="$(jq -r .name "$f")"; echo "trigger         $name"
  az datafactory trigger create -g "$RESOURCE_GROUP" --factory-name "$FACTORY" -n "$name" --properties "$(props "$f")" -o none
done

# Entity list read by the Lookup activity.
az storage blob upload --auth-mode login --account-name "$STORAGE_ACCOUNT_NAME" \
  -c config -n ingestion_config.json -f "$ROOT/config/ingestion_config.json" --overwrite -o none
echo "done"
