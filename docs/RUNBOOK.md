# Powerflow runbook

## Startup

1. Back up an existing database before schema changes.
2. Run `python -m alembic upgrade head`.
3. Start API, worker, scheduler and frontend through Compose or the Windows helper.
4. Verify `/health/live` and `/health/ready`; readiness must report database `ready`.

The application does not call `create_all` at startup. Alembic is the schema authority.

## Snapshot gap recovery

1. Run `taskflow snapshots-status`.
2. Backfill the exact missing interval with `taskflow backfill-snapshots --from ... --to ...`.
3. Recompute the covered interval with `taskflow recompute-metrics --from ... --to ...`.
4. Verify metric coverage and a reconciled drill-down before publishing narrative text.

Metric recomputation aborts if any daily calendar snapshot is absent.

## Worker or scheduler failure

- Inspect structured events `worker.cycle.failed` or `scheduler.cycle.failed`.
- Use `error_type`, failure count and retry delay; secrets and exception text are redacted.
- Confirm database readiness and migrations before restarting a process.
- Pending source items and signals remain durable in the database and are consumed after restart.

## Secret rotation

1. Stop processes that write credentials.
2. Export or reconnect external accounts; do not copy plaintext tokens into logs.
3. Replace `ENCRYPTION_KEY` through the deployment secret manager.
4. Reauthorize Microsoft so the encrypted cache is recreated under the new key.
5. Verify `/api/auth/status` returns metadata only.

Never store provider API keys in browser storage. Configure them in the protected backend
environment. In non-local environments the application rejects the development key,
wildcard CORS and Windows COM watchers.

## Migration rollback

Test upgrade and downgrade on a restored copy first. A rollback may remove constraints
or schema expected by newer binaries, so deploy the matching application version and
verify readiness before accepting traffic.