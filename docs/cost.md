# Cost guidance

The design favours consumption-based and auto-stopping resources. These are directional levers,
not a quote: price them for your region and usage with the
[Azure pricing calculator](https://azure.microsoft.com/pricing/calculator/).

| Lever | Setting in this repository |
| --- | --- |
| Batch compute stops when done | Jobs use job clusters (terminate after the run) and `availableNow` streaming triggers |
| Spot capacity | `SPOT_WITH_FALLBACK_AZURE` with one on-demand node |
| Autoscaling | 1 to 4 workers for jobs, enhanced autoscaling for DLT |
| Storage tiering | Lifecycle rules move `landing/` to cool after 30 days (delete after 180) and `archive/` to cool after 30 and archive after 365 days |
| Redundancy per environment | ZRS in dev, GZRS in prod |
| Log retention | 30 days in dev, 90 in prod |
| Event Hubs | Standard tier with auto-inflate capped at 4 throughput units |

Largest recurring cost drivers are normally Databricks compute (DBUs plus VMs), the Event Hubs
namespace, and Log Analytics ingestion. Tag every resource (`cost_center`, `environment`) and set a
budget alert on each resource group.
