# ADR 0005: Terraform for Azure, Asset Bundles for Databricks

- Status: accepted

## Decision
Terraform (azurerm) owns Azure resources and state in a remote backend. Databricks Asset Bundles
own jobs, pipelines and the wheel, because they version workspace objects together with the code
that they run. ADF definitions are plain JSON deployed by script, which keeps promotion
independent of ADF's publish branch.

## Consequences
- Three deployment mechanisms, each with its own workflow, but each with a clear owner.
- Bicep would be a valid alternative for the Azure layer; the module boundaries map one to one.
