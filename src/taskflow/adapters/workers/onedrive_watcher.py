import asyncio
import json
import os
import uuid
import structlog
from datetime import datetime

from taskflow.application.dto.commands import IngestSourceItemCommand
from taskflow.domain.value_objects.enums import SourceKind
from taskflow.config.container import AsyncSessionLocal
from taskflow.application.use_cases.ingest_source_item import IngestSourceItemUseCase

# Como é MVP e a fila é local fake
from tests.fakes import FakeQueue

log = structlog.get_logger()

# Diretório a ser monitorado
ONEDRIVE_PATH = r"C:\Users\WN6241\OneDrive - ENGIE\Powerflow\Inbox"

async def process_file(filepath: str):
    log.info("onedrive.found_file", filepath=filepath)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        data = {}
        body_lines = []
        is_body = False
        
        for line in lines:
            if is_body:
                body_lines.append(line)
            elif line.startswith("SUBJECT:"):
                data["subject"] = line[len("SUBJECT:"):].strip()
            elif line.startswith("SENDER_NAME:"):
                data["sender_name"] = line[len("SENDER_NAME:"):].strip()
            elif line.startswith("SENDER_EMAIL:"):
                data["sender_email"] = line[len("SENDER_EMAIL:"):].strip()
            elif line.startswith("MESSAGE_ID:"):
                data["message_id"] = line[len("MESSAGE_ID:"):].strip()
            elif line.startswith("RECEIVED_TIME:"):
                data["received_time"] = line[len("RECEIVED_TIME:"):].strip()
            elif line.startswith("BODY:"):
                is_body = True
                
        data["body"] = "".join(body_lines)
            
        async with AsyncSessionLocal() as session:
            # Instancia as dependências do banco manualmente
            from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
            from taskflow.adapters.persistence.task_repository import SqlAlchemyTaskRepository
            from taskflow.adapters.persistence.signal_repository import SqlAlchemySignalRepository
            
            uow = SqlAlchemyUnitOfWork(session)
            task_repo = SqlAlchemyTaskRepository(session)
            signal_repo = SqlAlchemySignalRepository(session)
            
            uc = IngestSourceItemUseCase(
                uow=uow,
                task_repo=task_repo,
                signal_repo=signal_repo,
                queue=FakeQueue()
            )
            
            occurred_at = datetime.utcnow()
            if data.get("received_time"):
                try:
                    occurred_at = datetime.fromisoformat(data["received_time"].replace('Z', '+00:00'))
                except ValueError:
                    pass
            
            message_id = data.get("message_id", str(uuid.uuid4()))
            
            cmd = IngestSourceItemCommand(
                kind=SourceKind.EMAIL,
                channel="onedrive_sync",
                external_id=message_id,
                occurred_at=occurred_at,
                revision_hash=message_id,
                title=data.get("subject"),
                body_full=data.get("body"),
                body_preview=data.get("body")[:500] if data.get("body") else None,
                author_email=data.get("sender_email"),
                author_name=data.get("sender_name"),
            )
            
            await uc.execute(cmd)
            
        # Apaga o arquivo após processar com sucesso (para não ler de novo)
        os.remove(filepath)
        log.info("onedrive.processed_and_deleted", filepath=filepath)
        
    except Exception as e:
        log.error("onedrive.process_error", filepath=filepath, error=str(e))
        # Se for um erro crítico, deletamos ou renomeamos para .error
        try:
            os.rename(filepath, filepath + ".error")
        except Exception:
            pass


async def watch_onedrive(interval_seconds: int = 5):
    """
    Loop que monitora a pasta do OneDrive procurando novos .json
    """
    log.info("onedrive.watcher_started", path=ONEDRIVE_PATH)
    
    if not os.path.exists(ONEDRIVE_PATH):
        try:
            os.makedirs(ONEDRIVE_PATH, exist_ok=True)
            log.info("onedrive.folder_created")
        except Exception as e:
            log.error("onedrive.folder_create_error", error=str(e))
            return
            
    while True:
        try:
            for filename in os.listdir(ONEDRIVE_PATH):
                if filename.endswith(".txt"):
                    filepath = os.path.join(ONEDRIVE_PATH, filename)
                    await process_file(filepath)
        except Exception as e:
            log.error("onedrive.loop_error", error=str(e))
            
        await asyncio.sleep(interval_seconds)
