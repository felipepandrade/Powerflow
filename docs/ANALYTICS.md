# Trustworthy analytics

Powerflow analytics read only published daily snapshots. Operational handlers do not
reconstruct dashboard values with ad-hoc joins.

## Read model

- `task_status_history` is the auditable source of truth.
- `daily_task_snapshots`, `daily_project_snapshots` and
  `daily_calendar_snapshots` are deterministic derived partitions.
- `metric_values` materializes a definition version, period and dimension.
- Re-running a published date is idempotent; the CLI supports explicit date ranges.

## Metric contract

Every API metric includes definition version, name, unit, data origin, formula, period,
dimension, value, numerator, denominator, sample size, coverage, suppression/unknown
state, caveat and provenance. Missing snapshot coverage aborts computation instead of
publishing a partial number.

Suppressed values remain `null`; unknown values remain `null`. Neither is converted to
zero. The LLM is never used for numeric calculation. Narrative and one-pager builders
accept only materialized facts and suppress output that fails grounding validation.

## Operations

```powershell
taskflow backfill-snapshots --from 2026-07-01 --to 2026-07-31
taskflow recompute-metrics --from 2026-07-01 --to 2026-07-31
taskflow snapshots-status
```

The scheduler publishes the most recently due partition, then computes metrics only
after the snapshot transaction succeeds. Failures are structured and retried with
bounded exponential backoff.