# ADR 0004: Managed identities, OIDC and private networking

- Status: accepted

## Decision
No shared keys or stored secrets: storage shared-key access is disabled, services use managed
identities, GitHub Actions authenticates with OIDC federation, and PaaS services are reached
through private endpoints. Databricks uses VNet injection with secure cluster connectivity.

## Consequences
- Smaller attack surface and nothing to rotate for platform access.
- Operations from outside the VNet (for example uploading Key Vault secrets) need a network path
  or a temporary firewall exception.
- Front-end Private Link for Databricks and Data Factory authoring is left as a documented
  production hardening step.
