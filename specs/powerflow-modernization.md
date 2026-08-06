# Powerflow modernization specification

## Objective

Bring Powerflow into demonstrably reliable alignment with `PRD.md` and `AGENTS.md`, preserving deterministic domain decisions and privacy while making the local SaaS operable end to end.

## Explicit exclusion

- Do not edit, remove, reconfigure, test, or otherwise change the OpenAI OAuth connection or its router/provider implementation. It will be evaluated separately by the product owner.

## Architecture and behavior requirements

- `domain/` remains free of application, adapter, framework, database, network, and provider dependencies.
- API, queue, application use cases, repositories, and domain entities use compatible typed contracts.
- Correlation executes ingestion -> extraction -> retrieval -> deterministic arbitration -> audited application without silent failure.
- LLM providers return validated, versioned structured assessments only; deterministic domain policies retain final authority.
- Literal evidence, candidate identity, allowed transition, confidence, and privacy guardrails run before automatic action.
- Every automatic task mutation stores enough history and evidence for a durable, idempotent Undo.
- Full source bodies are stored only when configuration explicitly permits it; private/confidential calendar content never enters LLM payloads.
- Source item deduplication is transactional and backed by a database uniqueness constraint.

## Product and analytics requirements

- Snapshots are historically reproducible and immutable once published, with corrections represented explicitly.
- Metrics have versioned formulas, numerator, denominator, coverage, dimensions, evidence and an unknown/suppressed state.
- Capacity ignores all-day events as specified and respects configured working hours, weekends, exclusions and timezone.
- Narratives and one-pagers never invent numbers and are suppressed when grounding validation fails.
- The UI shows only sourced values and real drill-downs; missing data is shown as unknown, never as zero or perfect health.
- Task status values, request contracts and period filters match the API and domain.
- Executive and perspective views are accessible and usable at common desktop and mobile widths.

## Security and operations requirements

- Microsoft authentication uses state/PKCE as appropriate and a persistable protected token cache; secrets are never logged or returned.
- API errors use a stable problem-details contract and do not leak internal exception text.
- Credentials are protected at rest; insecure public defaults are rejected outside explicit test mode.
- One production composition root is shared by local execution and containers; Windows-only watchers are environment-gated.
- Readiness checks real dependencies, the worker consumes work, and scheduled jobs have observable failure/retry behavior.
- CI enforces backend tests, coverage, domain coverage, strict typing, lint, migration smoke tests, frontend lint/build and contract tests.

## Milestones and binary definition of done

### M1 - Safe vertical core

- All command/response contracts compile under `mypy --strict` for the vertical core.
- An integration test proves ingestion -> extraction -> correlation -> task persistence -> audit -> Undo.
- Privacy and deduplication tests pass, including confidential calendar and duplicate revision cases.

### M2 - Trustworthy analytics

- Metric fixtures prove formulas, coverage and unknown/suppressed behavior.
- Historical snapshot/backfill tests prove the selected period is reconstructed from historical facts.
- Narrative and one-pager grounding tests prove unsupported numbers cannot be published.

### M3 - Honest product experience

- Frontend lint/build pass and no placeholder or fabricated managerial metric remains.
- API contract tests prove task state updates, snapshot dates, period filters and drill-down provenance.
- Accessibility checks cover navigation, dialogs, focus, labels and contrast-critical states.

### M4 - Production readiness

- A fresh database upgrades through Alembic and the selected application starts successfully.
- Container configuration is platform-correct and local Windows integrations are disabled outside local mode.
- CI gates pass with global coverage >= 80%, domain coverage >= 90%, strict typing and zero lint errors.
- A final PRD traceability review records implemented, deferred and externally blocked requirements.

## Verification loop

Maximum build-review rounds per milestone: 2 before escalating a genuinely repeated blocker. Evidence consists of automated tests, static checks, migration/startup smoke tests, API contract tests and frontend runtime verification. Production deployment, destructive data changes and external credential writes require separate approval.
