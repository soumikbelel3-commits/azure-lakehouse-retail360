# Deployment guide

Prerequisites: an Azure subscription (Owner or User Access Administrator plus Contributor for the
first run), Terraform 1.7+, Azure CLI with the `datafactory` extension, Databricks CLI, Python 3.10+.
Replace the placeholder values (`REPLACE_*`, `example.com`) in `databricks.yml`, the `*.tfvars`
files and `adf/` before deploying.

## 0. Bootstrap (once)

1. Create a resource group and storage account for Terraform state with a `tfstate` container;
   grant yourself and the CI identity **Storage Blob Data Contributor** on it.
2. Create an Entra app registration for GitHub Actions with **federated credentials** for the
   repository (entities `environment:dev` and `environment:prod`). Grant it Contributor and User
   Access Administrator on the target subscription or resource group.
3. In GitHub, create the environments `dev` and `prod` (require reviewers on `prod`) and set these
   environment variables: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`,
   `TFSTATE_RESOURCE_GROUP`, `TFSTATE_STORAGE_ACCOUNT`.

## 1. Infrastructure

```bash
cd infra/terraform
cp environments/backend-dev.hcl.example environments/backend-dev.hcl   # edit values
terraform init -backend-config=environments/backend-dev.hcl
terraform plan  -var-file=environments/dev.tfvars -var "subscription_id=$ARM_SUBSCRIPTION_ID"
terraform apply -var-file=environments/dev.tfvars -var "subscription_id=$ARM_SUBSCRIPTION_ID"
```

Or run the **Deploy infrastructure** workflow (plan first, then re-run with `apply`).

Manual steps Terraform cannot do:

- **Approve the ADF managed private endpoint** on the storage account
  (Networking > Private endpoint connections).
- **Register the self-hosted IR** on a VM that can reach the ERP database: fetch the key with
  `az datafactory integration-runtime list-auth-key` and enter it in the IR installer.
- Put the ERP SQL password in Key Vault as `erp-sql-password`. The vault has public access
  disabled, so do this from a network with a private endpoint route (or temporarily allow your IP).

## 2. Unity Catalog

```bash
databricks storage-credentials create --json '{
  "name": "retail360_mi",
  "azure_managed_identity": {"access_connector_id": "'"$(terraform output -raw databricks_access_connector_id)"'"}
}'
scripts/render_sql.sh sql/01_unity_catalog_foundation.sql retail360_dev "$(terraform output -raw storage_account_name)"
```

Run the rendered SQL in a SQL warehouse as a metastore admin. Run `02_pii_governance.sql` the
same way after the first successful pipeline run.

## 3. Databricks bundle

Fill the `workspace.host`, storage account names and (for prod) the service principal in
`databricks.yml` from the Terraform outputs, then:

```bash
databricks bundle validate -t dev
databricks bundle deploy   -t dev
databricks bundle run retail360_daily -t dev
```

For the Event Hubs stream, create a secret scope with `sp-tenant-id`, `sp-client-id` and
`sp-client-secret` for a service principal that has **Azure Event Hubs Data Receiver** on the
namespace, and set the bundle variable `eventhubs_namespace`.

## 4. Data Factory

```bash
RESOURCE_GROUP=$(terraform output -raw resource_group_name) \
FACTORY=$(terraform output -raw data_factory_name) \
STORAGE_ACCOUNT_NAME=$(terraform output -raw storage_account_name) \
KEY_VAULT_NAME=$(terraform output -raw key_vault_name) \
ERP_SQL_HOST=erp-sql.corp.example.com \
scripts/deploy_adf.sh
az datafactory trigger start -g "$RESOURCE_GROUP" --factory-name "$FACTORY" -n TR_Daily_Tumbling
```

Add the ADF managed identity to the Databricks workspace as a service principal with
permission to run the job (the master pipeline calls the Jobs API with it), then set the
`databricksWorkspaceUrl` and `databricksJobId` pipeline parameters.

## 5. Try it without a cloud: local run

```bash
pip install -e ".[dev]"
python scripts/generate_sample_data.py      # regenerates data/sample deterministically
pytest
```

The tests execute the full Silver and Gold logic on the sample files with a local Spark session.

## Teardown

`terraform destroy -var-file=environments/dev.tfvars ...`. The resource group has
`prevent_deletion_if_contains_resources`, so Terraform removes resources first. Key Vault is
soft-deleted; purge it if you want to reuse the name.
