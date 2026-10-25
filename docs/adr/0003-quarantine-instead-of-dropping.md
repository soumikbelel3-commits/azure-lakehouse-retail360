# ADR 0003: Quarantine rejected rows

- Status: accepted

## Context
Silently dropping bad records hides upstream problems and makes reconciliation impossible.

## Decision
Rules are split into blocking (row quarantined) and warning (row kept, rate tracked). Rejected rows
are written to `<entity>_quarantine` tables with the list of failed rules. A separate DQ job
publishes pass rates and fails the run below a threshold.

## Consequences
- Every source row is accounted for: valid + quarantined = ingested.
- Slightly more storage and one more table per entity.
- Rules live in one Python module and are tested, so DLT, jobs and tests cannot drift.
