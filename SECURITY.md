# Security policy

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's **Report a vulnerability** button (private
security advisories) on this repository. Expect an acknowledgement within a few days.

## Security posture of the reference implementation

- No credentials in the repository: Azure access uses OIDC federation and managed identities.
  Secrets (for example the ERP SQL password) live in Azure Key Vault.
- Shared storage keys are disabled; ADLS is reached with Microsoft Entra identities only.
- PaaS services sit behind private endpoints; Databricks uses VNet injection and secure cluster
  connectivity (no public IPs).
- Unity Catalog enforces table and column permissions, with masking of direct identifiers.

See [docs/security.md](docs/security.md) for the full model and known gaps.
