# Powerflow modernization traceability

Date: 2026-08-05

This review maps the binary modernization scope in `specs/powerflow-modernization.md`
to implementation and automated evidence. `PRD.md` remains the product reference and
`AGENTS.md` remains the architecture constraint.

## Implemented

| Scope | Implementation | Evidence |
|---|---|---|
| Hexagonal boundary | Domain remains independent from adapters, application and I/O libraries. | `tests/architecture/test_domain_boundaries.py`; domain coverage gate. |
| Typed vertical flow | Compatible DTO, router, queue, use-case and repository contracts. | `mypy --strict src apps`; `tests/integration/adapters/test_m1_vertical.py`. |
| Deterministic correlation | LLM output is assessment only; the final matrix remains in `domain/policies/correlation_policy.py`. | RF-G.8 unit cases and vertical integration test. |
| Guardrails and privacy | Literal evidence, candidate identity, transition safety and confidence gates precede mutation; private/confidential content is blocked before LLM use. | M1 vertical privacy spy and domain guardrail tests. |
| Durable audit and Undo | Evidence, updates, correlation runs and status history are persisted; automatic history is reversible and Undo is idempotent. | M1 vertical test covers exact restoration and repeated Undo. |
| Transactional deduplication | Source revision and evidence uniqueness are enforced in application/repository code and database constraints. | Alembic revision `6f4c9b2a1d30`; duplicate-revision integration test. |
| Historical analytics | Daily task, project and calendar snapshots are derived from historical facts and rebuilt deterministically. | Snapshot/backfill tests and migration smoke. |
| Trustworthy metrics | Versioned definitions expose formula, unit, origin, numerator, denominator, sample, coverage, caveat, state and provenance. | `test_trustworthy_analytics.py`; analytics API contract tests. |
| Capacity | Working hours, work days, timezone, overlap, declined/free and all-day handling are deterministic. | Capacity policy and snapshot tests. |
| Grounded text | Narrative and one-pager generation fail closed when numbers cannot be reconciled. | Narrative and one-pager grounding tests. |
| Honest accessible UI | No fabricated 0/100 fallback; task status is `done`; real filters, reconciled drill-downs, unknown/suppressed states, keyboard/focus behavior and responsive views. | Frontend lint/build and browser smoke at desktop and 390 px. |
| Microsoft auth | State and PKCE flow, encrypted persisted auth flow and protected serializable token cache. | `test_microsoft_auth.py`; credential encryption tests. |
| API hardening | Explicit CORS, problem-details errors without internal exception text, liveness and real database readiness. | Problem-details contract and startup smoke. |
| Operations | Shared composition root, non-root images, migration-first Compose, durable DB-polling worker, snapshot/metric scheduler with retry logging, CLI and CI gates. | Process smoke, Compose config, CLI smoke and CI workflow. |
| Secret handling | AES-GCM credential envelope, structured-log redaction, insecure public defaults rejected, browser API-key storage removed. | Security unit tests and source audit. |

## Verification evidence

- Backend suite excluding the explicitly protected OpenAI OAuth test: 196 tests passed.
- Global coverage: 82.21% (required 80%).
- Domain coverage: 90.69% (required 90%).
- Ruff: zero findings.
- Mypy strict: zero findings across `src` and `apps`.
- Frontend: lint and production build passed.
- Fresh SQLite: upgrade to head, downgrade to base, upgrade to head and Alembic drift check passed.
- Startup: liveness and database readiness returned HTTP 200.
- Worker/scheduler: empty durable consumption plus snapshot-then-metrics process smoke passed.
- Browser: Today, Calendar and capacity Cockpit loaded with meaningful content, no Vite overlay, no console errors and no horizontal overflow at 390 px.

## Explicit exclusion

The OpenAI subscription OAuth connection, including `oauth_openai.py`, its provider and
its behavior, was not changed or tested. It remains product-owner work by explicit request.

## Externally blocked validation

| Item | Status | Required external action |
|---|---|---|
| Local Docker image build | Compose configuration is valid; build could not run because the Docker daemon was not running. | Start Docker Desktop and run `docker compose -f infra/compose/local.yml build`. |
| Real Microsoft authorization and Graph data | Automated state/PKCE/cache tests pass; no tenant app registration or user credentials were supplied. | Configure the Azure app registration and execute the consent flow in the target tenant. |
| Production PostgreSQL deployment | Async PostgreSQL dependency and migration path are configured; no managed database or deployment target was supplied. | Provision the target database, run migrations, parity tests and backup/restore drill. |

## Product expansion beyond this modernization

The local mini-SaaS path is complete for the modernization specification. Scale-out
features described in the long-form PRD—distributed Redis/ARQ claiming, PostgreSQL
partition automation, pgvector indexing, managed deployment and real Microsoft Graph
delta synchronization—remain deployment/scale work, not silent local fallbacks. Their
absence is surfaced operationally and does not fabricate product data.