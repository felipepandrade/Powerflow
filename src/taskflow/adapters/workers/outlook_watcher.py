import asyncio
from datetime import UTC, datetime, timedelta

import pythoncom
import structlog
import win32com.client

from taskflow.adapters.queue.in_process_queue import InProcessQueue
from taskflow.application.dto.commands import IngestSourceItemCommand
from taskflow.application.use_cases.ingest_source_item import IngestSourceItemUseCase
from taskflow.config.container import AsyncSessionLocal
from taskflow.domain.value_objects.enums import CalendarSensitivity, SourceKind

log = structlog.get_logger()

PROCESSED_ENTRY_IDS: set[str] = set()
PROCESSED_CALENDAR_IDS: set[str] = set()


def poll_outlook_sync() -> tuple[list[dict], list[dict]]:
    """Função síncrona em thread isolada para interagir com Outlook COM.

    Retorna (novos_emails, novos_eventos_calendario).
    """
    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")

        # 1. E-mails (Inbox = 6)
        inbox = namespace.GetDefaultFolder(6)
        messages = inbox.Items.Restrict("[Unread]=true")
        new_emails = []

        for msg in messages:
            try:
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
                    "received_time": msg.ReceivedTime.isoformat() if hasattr(msg, "ReceivedTime") else None,
                })
            except Exception as e:
                log.error("outlook.email_parse_error", error=str(e))
                continue

        # 2. Calendário (Calendar = 9)
        calendar_folder = namespace.GetDefaultFolder(9)
        events = calendar_folder.Items
        events.IncludeRecurrences = True
        events.Sort("[Start]")

        # Filtrar janela: -7 dias até +30 dias
        now = datetime.now()
        start_range = (now - timedelta(days=7)).strftime("%m/%d/%Y %H:%M %p")
        end_range = (now + timedelta(days=30)).strftime("%m/%d/%Y %H:%M %p")
        restricted_events = events.Restrict(f'[Start] >= "{start_range}" AND [End] <= "{end_range}"')

        new_events = []
        for evt in restricted_events:
            try:
                entry_id = getattr(evt, "EntryID", None)
                if not entry_id:
                    continue

                # Identificador único por data de início para instâncias recorrentes
                start_iso = evt.Start.isoformat() if hasattr(evt, "Start") else ""
                event_key = f"{entry_id}:{start_iso}"

                if event_key in PROCESSED_CALENDAR_IDS:
                    continue

                PROCESSED_CALENDAR_IDS.add(event_key)

                sensitivity_raw = getattr(evt, "Sensitivity", 0)
                # 0=olNormal, 1=olPersonal, 2=olPrivate, 3=olConfidential
                sens_map = {
                    0: CalendarSensitivity.NORMAL,
                    1: CalendarSensitivity.PERSONAL,
                    2: CalendarSensitivity.PRIVATE,
                    3: CalendarSensitivity.CONFIDENTIAL,
                }
                sensitivity = sens_map.get(sensitivity_raw, CalendarSensitivity.NORMAL)

                new_events.append({
                    "event_id": event_key,
                    "graph_event_id": entry_id,
                    "subject": getattr(evt, "Subject", "Reunião sem título"),
                    "body": getattr(evt, "Body", ""),
                    "location": getattr(evt, "Location", ""),
                    "starts_at": evt.Start.isoformat() if hasattr(evt, "Start") else None,
                    "ends_at": evt.End.isoformat() if hasattr(evt, "End") else None,
                    "is_all_day": getattr(evt, "AllDayEvent", False),
                    "sensitivity": sensitivity.value,
                    "organizer": getattr(evt, "Organizer", ""),
                    "is_recurring": getattr(evt, "IsRecurring", False),
                })
            except Exception as e:
                log.error("outlook.calendar_parse_error", error=str(e))
                continue

        return new_emails, new_events
    finally:
        pythoncom.CoUninitialize()


async def watch_outlook(interval_seconds: int = 5) -> None:
    """Loop principal de monitoramento de e-mail e calendário do Outlook."""
    log.info("outlook.watcher_started")

    while True:
        try:
            new_emails, new_events = await asyncio.to_thread(poll_outlook_sync)

            if new_emails or new_events:
                log.info("outlook.activity_detected", emails=len(new_emails), events=len(new_events))

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

                    # Ingerir E-mails
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

                    # Ingerir Eventos de Calendário
                    for evt_data in new_events:
                        starts_at = datetime.utcnow()
                        ends_at = datetime.utcnow()
                        if evt_data.get("starts_at"):
                            try:
                                starts_at = datetime.fromisoformat(evt_data["starts_at"]).astimezone(UTC).replace(tzinfo=None)
                            except ValueError:
                                pass
                        if evt_data.get("ends_at"):
                            try:
                                ends_at = datetime.fromisoformat(evt_data["ends_at"]).astimezone(UTC).replace(tzinfo=None)
                            except ValueError:
                                pass

                        cmd = IngestSourceItemCommand(
                            kind=SourceKind.CALENDAR_EVENT,
                            channel="outlook_calendar_local",
                            external_id=evt_data["event_id"],
                            occurred_at=starts_at,
                            revision_hash=evt_data["event_id"],
                            title=evt_data.get("subject"),
                            body_full=evt_data.get("body"),
                            body_preview=evt_data.get("body")[:500] if evt_data.get("body") else None,
                            author_name=evt_data.get("organizer"),
                            calendar_starts_at=starts_at,
                            calendar_ends_at=ends_at,
                            calendar_is_all_day=evt_data.get("is_all_day", False),
                            calendar_sensitivity=evt_data.get("sensitivity"),
                        )
                        await uc.execute(cmd)

        except Exception as e:
            log.error("outlook.loop_error", error=str(e))

        await asyncio.sleep(interval_seconds)
