import asyncio
from datetime import UTC, datetime

import pythoncom
import structlog
import win32com.client

from taskflow.adapters.queue.in_process_queue import InProcessQueue
from taskflow.application.dto.commands import IngestSourceItemCommand
from taskflow.application.use_cases.ingest_source_item import IngestSourceItemUseCase
from taskflow.config.container import AsyncSessionLocal
from taskflow.domain.value_objects.enums import SourceKind

log = structlog.get_logger()

# Armazenar EntryIDs já processados para não processar duas vezes.
# No futuro isso iria pro banco de dados, mas no MVP podemos usar em memória.
PROCESSED_ENTRY_IDS = set()

def poll_outlook_sync():
    """
    Função síncrona que roda em uma thread isolada para interagir com o COM.
    Retorna uma lista de dicionários contendo os dados dos emails novos.
    """
    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        inbox = namespace.GetDefaultFolder(6)  # 6 = olFolderInbox
        
        # Filtra apenas não lidos
        messages = inbox.Items.Restrict("[Unread]=true")
        
        new_emails = []
        
        for msg in messages:
            try:
                # msg.MessageClass == 'IPM.Note' serve para pegar apenas emails, não convites de cal.
                if getattr(msg, "MessageClass", "") != "IPM.Note":
                    continue
                    
                entry_id = getattr(msg, "EntryID", None)
                if not entry_id or entry_id in PROCESSED_ENTRY_IDS:
                    continue
                    
                PROCESSED_ENTRY_IDS.add(entry_id)
                
                new_emails.append({
                    "message_id": entry_id,
                    "subject": getattr(msg, "Subject", "Sem Assunto"),
                    "body": getattr(msg, "Body", ""),
                    "sender_name": getattr(msg, "SenderName", ""),
                    "sender_email": getattr(msg, "SenderEmailAddress", ""),
                    "received_time": msg.ReceivedTime.isoformat() if hasattr(msg, "ReceivedTime") else None
                })
            except Exception as e:
                log.error("outlook.msg_parse_error", error=str(e))
                continue
                
        return new_emails
    finally:
        pythoncom.CoUninitialize()


async def watch_outlook(interval_seconds: int = 5):
    """
    Loop que monitora o Outlook local procurando novos e-mails não lidos.
    """
    log.info("outlook.watcher_started")
    
    while True:
        try:
            # Chama a função COM em uma thread separada para não travar o event loop
            new_emails = await asyncio.to_thread(poll_outlook_sync)
            
            if new_emails:
                log.info("outlook.new_emails_found", count=len(new_emails))
                
                async with AsyncSessionLocal() as session:
                    from taskflow.adapters.persistence.signal_repository import (
                        SqlAlchemySignalRepository,
                    )
                    from taskflow.adapters.persistence.task_repository import (
                        SqlAlchemyTaskRepository,
                    )
                    from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
                    
                    uow = SqlAlchemyUnitOfWork(session)
                    task_repo = SqlAlchemyTaskRepository(session)
                    signal_repo = SqlAlchemySignalRepository(session)
                    
                    uc = IngestSourceItemUseCase(
                        uow=uow,
                        task_repo=task_repo,
                        signal_repo=signal_repo,
                        queue=InProcessQueue()
                    )
                    
                    for email_data in new_emails:
                        occurred_at = datetime.utcnow()
                        if email_data.get("received_time"):
                            try:
                                dt_str = email_data["received_time"]
                                occurred_at = datetime.fromisoformat(dt_str).astimezone(UTC).replace(tzinfo=None)
                            except ValueError:
                                pass
                        
                        cmd = IngestSourceItemCommand(
                            kind=SourceKind.EMAIL,
                            channel="outlook_local",
                            external_id=email_data["message_id"],
                            occurred_at=occurred_at,
                            revision_hash=email_data["message_id"],
                            title=email_data.get("subject"),
                            body_full=email_data.get("body"),
                            body_preview=email_data.get("body")[:500] if email_data.get("body") else None,
                            author_email=email_data.get("sender_email"),
                            author_name=email_data.get("sender_name"),
                        )
                        
                        await uc.execute(cmd)
                        log.info("outlook.email_ingested", message_id=email_data["message_id"])
                        
        except Exception as e:
            log.error("outlook.loop_error", error=str(e))
            
        await asyncio.sleep(interval_seconds)
