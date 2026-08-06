# Powerflow

Powerflow is a local-first mini-SaaS for reliable task capture, deterministic
correlation, auditable automation, and grounded managerial analytics.

The domain layer is the source of truth. LLM providers may return structured
hypotheses and literal evidence, but final correlation decisions and every
numeric metric are deterministic code.

## Local quickstart

Requirements:

- Python 3.12+
- Node.js 22+
- Docker Desktop (optional)

Create the environment file and replace the encryption key before using real
credentials:

```powershell
Copy-Item .env.example .env
python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Then use the Windows helpers:

```powershell
.\setup_env.bat
.\start_powerflow.bat
```

The UI is available at `http://localhost:5173` and the API at
`http://localhost:8080`.

## Docker Compose

```powershell
docker compose -f infra/compose/local.yml up --build
```

Compose runs a migration job before starting the API, worker, scheduler, and
frontend. Windows COM watchers are disabled in containers.

## Database migrations

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

The application never creates production tables implicitly. Alembic is the only
schema authority.

## Quality gates

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src apps
.\.venv\Scripts\python.exe -m pytest --ignore=tests\unit\adapters\test_chatgpt_subscription.py --cov=src\taskflow --cov-fail-under=80
.\.venv\Scripts\python.exe -m pytest tests\unit\domain --cov=src\taskflow\domain --cov-fail-under=90
npm --prefix frontend run lint
npm --prefix frontend run build
```

The OpenAI subscription OAuth connection is intentionally outside these
modernization gates and remains unchanged.

## Architecture

- `src/taskflow/domain`: pure entities, value objects, policies, metric
  definitions, and ports. No framework, database, network, or provider imports.
- `src/taskflow/application`: typed commands, results, and use-case
  orchestration.
- `src/taskflow/adapters`: API, persistence, queues, providers, and local
  watchers.
- `apps`: shared runtime entrypoints for API, worker, scheduler, and CLI.
- `frontend`: React cockpit with explicit known, unknown, and suppressed data
  states.

## Safety and privacy

- Private and confidential calendar content is reduced to an opaque capacity
  block before any LLM call.
- Source revisions are deduplicated transactionally.
- Automatic mutations store evidence and history and support durable,
  idempotent Undo.
- Credentials and Microsoft token cache entries are AES-GCM encrypted at rest.
- API failures use `application/problem+json` and never return internal
  exception text.
- Managerial metrics include coverage, formula, numerator, denominator,
  suppression state, and provenance.
