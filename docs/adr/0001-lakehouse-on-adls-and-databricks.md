# ADR 0001: Delta lakehouse on ADLS Gen2 with Azure Databricks

- Status: accepted

## Context
We need one platform for BI, ML and streaming over the same data, with open table formats and
strong governance.

## Decision
Store all layers as Delta tables on ADLS Gen2 and process them with Azure Databricks (Premium) and
Unity Catalog. Use the medallion pattern: Bronze (raw), Silver (clean), Gold (modelled).

## Consequences
- One copy of data serves SQL, BI and ML; Delta gives ACID, time travel and MERGE.
- Databricks Premium is required for Unity Catalog and private networking, which costs more than
  the Standard tier.
- Alternatives considered: Synapse dedicated SQL pool (strong SQL, weaker for ML and streaming),
  Microsoft Fabric (attractive, but ties compute and governance to one vendor stack).
