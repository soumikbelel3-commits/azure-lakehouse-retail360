# Security and governance

## Identity

| Principal | Used for | Access |
| --- | --- | --- |
| GitHub OIDC app registration | CI/CD deployments | Contributor on the environment resource group; no client secret |
| ADF managed identity | Copy to landing, Key Vault reads | Storage Blob Data Contributor, Key Vault Secrets User |
| Databricks access connector | Unity Catalog storage credential | Storage Blob Data Contributor |
| Event Hubs managed identity | Capture to `archive` | Storage Blob Data Contributor |
| Entra groups | People | `data-engineers`, `data-analysts`, `data-scientists`, `pii-readers` mapped to Unity Catalog grants |

The Terraform role assignments are intentionally scoped to the storage account rather than the
subscription. For stricter isolation, assign at container level with ABAC conditions.

## Network

- Single VNet with three subnets: two delegated to Databricks (VNet injection, secure cluster
  connectivity, no public IPs) and one for private endpoints.
- Private endpoints for ADLS (`dfs`, `blob`), Key Vault and Event Hubs, with private DNS zones
  linked to the VNet. Public network access is disabled on those three services.
- ADF uses a managed virtual network integration runtime and a managed private endpoint to ADLS
  (needs a one-time approval, see the deployment guide).
- **Known gap:** the Databricks workspace and ADF studio keep public access for authoring
  (`databricks_public_network_access = true`). Production should add Front-end Private Link and a
  VPN or jump host, then flip that variable.

## Data protection

- Encryption at rest with Microsoft-managed keys (infrastructure encryption enabled on ADLS).
  Customer-managed keys are a documented extension, not implemented.
- TLS 1.2 minimum; shared key and anonymous access disabled on storage.
- Soft delete on blobs and containers (14 days) and Key Vault (90 days, purge protection in prod).
- Unity Catalog column masks on direct identifiers, tags on sensitive columns.

## Secrets

The repository contains no secrets. The ERP SQL password is a Key Vault secret named
`erp-sql-password` referenced by the linked service. The Event Hubs Kafka reader needs a service
principal whose id, tenant and secret are kept in a Databricks secret scope backed by Key Vault.
CI scans every push with gitleaks.

## Audit and monitoring

Diagnostic settings send ADF, Key Vault, Event Hubs and blob logs to Log Analytics. Databricks
audit logs are available through Unity Catalog system tables. See the [runbook](runbook.md) for
alerts and queries.
