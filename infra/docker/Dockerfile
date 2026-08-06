FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip wheel --wheel-dir /wheels .

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src:/app \
    APP_ENV=local \
    ENABLE_LOCAL_WINDOWS_WATCHERS=false

WORKDIR /app
RUN addgroup --system powerflow && adduser --system --ingroup powerflow powerflow
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY apps ./apps
RUN mkdir -p /app/data && chown -R powerflow:powerflow /app

USER powerflow
EXPOSE 8080

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
