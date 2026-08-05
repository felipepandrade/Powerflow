"""Worker de monitoramento de mensagens do Teams via Outlook COM (Conversation History)."""

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

PROCESSED_TEAMS_IDS: set[str] = set()


def poll_teams_sync() -> list[dict]:
    """Busca conversas e chats do Teams sincronizados na pasta 'Conversation History' do Outlook COM."""
    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")

        # Procura a pasta "Histórico de Conversas" / "Conversation History"
        inbox = namespace.GetDefaultFolder(6)
        parent = inbox.Parent
        conv_folder = None

        for folder in parent.Folders:
            name_lower = folder.Name.lower()
            if "convers" in name_lower or "teams" in name_lower or "skype" in name_lower:
                conv_folder = folder
                break

        if not conv_folder:
            return []

        messages = conv_folder.Items
        new_chats = []

        for msg in messages:
            try:
                entry_id = getattr(msg, "EntryID", None)
                if not entry_id or entry_id in PROCESSED_TEAMS_IDS:
                    continue

                PROCESSED_TEAMS_IDS.add(entry_id)

                new_chats.append({
                    "chat_id": entry_id,
                    "subject": getattr(msg, "Subject", "Chat Teams"),
                    "body": getattr(msg, "Body", ""),
                    "sender_name": getattr(msg, "SenderName", ""),
                    "sender_email": getattr(msg, "SenderEmailAddress", ""),
                    "received_time": msg.ReceivedTime.isoformat() if hasattr(msg, "ReceivedTime") else None,
                })
            except Exception as e:
                log.error("teams.msg_parse_error", error=str(e))
                continue

        return new_chats
    except Exception as e:
        log.warning("teams.folder_not_found", detail=str(e))
        return []
    finally:
        pythoncom.CoUninitialize()


async def watch_teams(interval_seconds: int = 15) -> None:
    """Loop principal de monitoramento de mensagens do Teams via COM."""
    log.info("teams.watcher_started")

    while True:
        try:
            new_chats = await asyncio.to_thread(poll_teams_sync)

            if new_chats:
                log.info("teams.new_chats_found", count=len(new_chats))

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
                        queue=InProcessQueue(),
                    )

                    for chat_data in new_chats:
                        occurred_at = datetime.utcnow()
                        if chat_data.get("received_time"):
                            try:
                                dt_str = chat_data["received_time"]
                                occurred_at = datetime.fromisoformat(dt_str).astimezone(UTC).replace(tzinfo=None)
                            except ValueError:
                                pass

                        cmd = IngestSourceItemCommand(
                            kind=SourceKind.TEAMS_CHAT,
                            channel="teams_local",
                            external_id=chat_data["chat_id"],
                            occurred_at=occurred_at,
                            revision_hash=chat_data["chat_id"],
                            title=chat_data.get("subject"),
                            body_full=chat_data.get("body"),
                            body_preview=chat_data.get("body")[:500] if chat_data.get("body") else None,
                            author_email=chat_data.get("sender_email"),
                            author_name=chat_data.get("sender_name"),
                        )
                        await uc.execute(cmd)
                        log.info("teams.chat_ingested", chat_id=chat_data["chat_id"])

        except Exception as e:
            log.error("teams.loop_error", error=str(e))

        await asyncio.sleep(interval_seconds)
