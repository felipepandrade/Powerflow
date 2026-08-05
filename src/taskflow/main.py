import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from taskflow.adapters.api.routers import (
    auth_router,
    signals_router,
    system_router,
    tasks_router,
    webhook_router,
)
from taskflow.adapters.persistence.models import Base
from taskflow.adapters.workers.outlook_watcher import watch_outlook
from taskflow.config.container import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa as tabelas do banco de dados na inicialização do app
    # Em produção, usariamos Alembic. Para o MVP SQLite, create_all() é suficiente.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Inicia o background worker do Outlook Local
    watcher_task = asyncio.create_task(watch_outlook(interval_seconds=5))
    
    yield
    
    # Limpeza, caso necessária
    watcher_task.cancel()
    await engine.dispose()


app = FastAPI(
    title="TaskFlow API",
    description="Sistema Pessoal de Captura Autônoma e Gestão Correlacionada de Tarefas",
    version="0.1.0",
    lifespan=lifespan,
)

# Configuração de CORS (Permitir tudo para ambiente de dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Acoplando roteadores
app.include_router(signals_router.router)
app.include_router(tasks_router.router)
app.include_router(system_router.router)
app.include_router(auth_router.router)
app.include_router(webhook_router.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}

@app.get("/health/live")
async def health_live():
    return {"status": "alive", "env": "local", "version": "0.1.0"}

@app.get("/health/ready")
async def health_ready():
    # Aqui poderíamos checar conexões com banco/serviços
    return {"status": "ready", "env": "local", "version": "0.1.0"}
