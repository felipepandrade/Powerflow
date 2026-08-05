from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações centralizadas da aplicação TaskFlow baseadas em pydantic-settings."""

    # ── Aplicação ───────────────────────────────────────────────────────
    APP_ENV: str = "local"
    LOG_LEVEL: str = "INFO"
    ENCRYPTION_KEY: str = "c29tZV9zZWNyZXRfa2V5XzMyX2J5dGVzX2xvbmdfMTIzNDU2Nzg="

    # ── Persistência ────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/taskflow.db"
    QUEUE_BACKEND: str = "inprocess"
    REDIS_URL: str | None = None

    # ── Microsoft Graph ─────────────────────────────────────────────────
    MS_CLIENT_ID: str = ""
    MS_CLIENT_SECRET: str = ""
    MS_TENANT_ID: str = "common"
    MS_REDIRECT_URI: str = "http://localhost:8000/api/auth/callback"
    SYNC_INTERVAL_MINUTES: int = 15

    # ── LLM: Gemini (default) ───────────────────────────────────────────
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    OLLAMA_MODEL: str = "llama3.1:8b"
    LLM_MODEL_CLASSIFIER: str = "gemini-2.5-flash"
    LLM_MODEL_REASONER: str = "gemini-2.5-pro"
    LLM_VALIDATE_MODEL_ON_STARTUP: bool = False
    LLM_THINKING_BUDGET_CLASSIFY: int = 0
    LLM_THINKING_BUDGET_EXTRACT: int = 1024
    LLM_THINKING_BUDGET_CORRELATE: int = 2048
    LLM_ENABLE_CONTEXT_CACHE: bool = True
    LLM_MAX_RETRIES: int = 4
    LLM_SAFETY_THRESHOLD: str = "BLOCK_ONLY_HIGH"
    DAILY_TOKEN_BUDGET: int = 200000

    # ── Embeddings ──────────────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_DIM: int = 768

    # ── Privacidade e retenção ──────────────────────────────────────────
    STORE_FULL_BODY: bool = False
    RETENTION_DAYS: int = 180

    # ── Ingestão: calendário ────────────────────────────────────────────
    CALENDAR_ENABLED: bool = True
    CALENDAR_WINDOW_PAST_DAYS: int = 30
    CALENDAR_WINDOW_FUTURE_DAYS: int = 90
    CALENDAR_INCLUDE_PRIVATE: bool = False
    CALENDAR_MIN_ATTENDEES_FOR_EXTRACTION: int = 2

    # ── Capacidade ──────────────────────────────────────────────────────
    WORK_HOURS_START: str = "08:30"
    WORK_HOURS_END: str = "18:00"
    WORK_DAYS: str = "1,2,3,4,5"
    CAPACITY_BUFFER_MINUTES: int = 60

    # ── Extração ────────────────────────────────────────────────────────
    EXTRACTION_MIN_CONFIDENCE: float = 0.55

    # ── Correlação ──────────────────────────────────────────────────────
    CORRELATION_TOP_K: int = 8
    CORRELATION_RRF_K: int = 60
    CORR_AUTO_UPDATE_MIN: float = 0.80
    CORR_AUTO_TRANSITION_MIN: float = 0.85
    CORR_AUTO_DONE_MIN: float = 0.90
    CORR_NEW_TASK_MIN: float = 0.85
    CORR_ATTACH_CONTEXT_MIN: float = 0.60
    CORR_NOISE_MIN: float = 0.70
    CORR_DISCARD_MAX: float = 0.55
    CORR_AMBIGUITY_DELTA: float = 0.10
    SIGNAL_PENDING_TTL_DAYS: int = 7
    ALLOW_AUTO_DONE: bool = True
    ALLOW_AUTO_CANCEL: bool = False

    # ── Follow-up ───────────────────────────────────────────────────────
    STALENESS_WAITING_DAYS: int = 3
    STALENESS_IN_PROGRESS_DAYS: int = 7
    STALENESS_BLOCKED_DAYS: int = 5
    PREFER_MEETING_OVER_EMAIL_HOURS: int = 48
    NUDGE_TONE: str = "cordial"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Retorna uma instância singleton com as configurações da aplicação."""
    return Settings()
