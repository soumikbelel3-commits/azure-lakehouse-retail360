# Operations runbook

## Alerts

| Alert | Source | First action |
| --- | --- | --- |
| `PipelineFailedRuns > 0` | Azure Monitor metric alert on ADF (severity 2) | Open the failed run in ADF Monitor, find the failing entity, see "Ingestion failures" |
| Job failure email | Databricks job `retail360-daily` | Open the run; the failing task name tells you the layer |
| `retail360-dq` exits 1 | `dq_gate` task | Query `gold.dq_results` for the breached rule, see "Quality breach" |

## Ingestion failures

1. In ADF Monitor, filter by pipeline `PL_Ingest_Entity` and read the Copy activity error.
2. Connectivity to the ERP: check the self-hosted IR node status (`ir-onprem-shir`) and the
   `erp-sql-password` secret.
3. Re-run only the failed window: tumbling-window triggers support **Rerun**, which re-executes
   the same `windowStart`/`windowEnd`. If the window failed before writing, the rerun simply
   produces the file. If a file was already ingested and the source was corrected, note that Auto
   Loader ignores overwritten files by default: either enable `cloudFiles.allowOverwrites` for
   that run, or delete the affected Bronze rows and checkpoint entry and re-ingest.

## Quality breach

```sql
SELECT entity, rule, kind, pass_rate, run_ts
FROM   retail360_prod.gold.dq_results
WHERE  run_ts > current_timestamp() - INTERVAL 1 DAY AND pass_rate < 0.95
ORDER  BY run_ts DESC;
```

Inspect rejected rows and the rules they failed:

```sql
SELECT _dq_failed_rules, count(*) AS rows
FROM   retail360_prod.silver.orders_quarantine
GROUP  BY 1 ORDER BY rows DESC;
```

If the source is wrong, fix it upstream and rerun the window. If the rule is wrong, change it in
`quality.py`, add a test, and deploy; then refresh the Silver pipeline.

## Replays and backfills

- **Batch:** rerun ADF windows for the date range (tumbling-window backfill is built in).
- **Streaming:** Event Hubs retains 1 day; older events are in `archive/` as Avro. Replay by
  pointing a one-off Auto Loader job (`cloudFiles.format = avro`) at the archive path.
- **Full Silver refresh:** run the DLT pipeline with `full_refresh: true`. Bronze is append-only,
  so Silver can always be rebuilt from it.

## Routine tasks

| Task | How |
| --- | --- |
| Rotate the ERP password | Update the Key Vault secret; no pipeline change |
| Add a source table | Add a row to `adf/config/ingestion_config.json`, add the entity to `schemas.py`, `quality.py` and `silver.py`, add tests |
| Vacuum Delta tables | Predictive optimization handles it in Unity Catalog; otherwise schedule `VACUUM` weekly |
| Disaster recovery | Prod storage is GZRS. Redeploy infrastructure from Terraform into the paired region, restore data from the GZRS secondary, and re-point the bundle variables |

## Useful Log Analytics query

```kusto
ADFPipelineRun
| where TimeGenerated > ago(1d) and Status == "Failed"
| project TimeGenerated, PipelineName, RunId, FailureType
| order by TimeGenerated desc
```
