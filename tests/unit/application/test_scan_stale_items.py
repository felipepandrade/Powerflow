"""Testes de integração para ScanStaleItemsUseCase — UC-5."""

import uuid
from datetime import datetime, timedelta

import pytest

from taskflow.application.dto.commands import ScanStaleItemsCommand
from taskflow.application.use_cases.scan_stale_items import ScanStaleItemsUseCase
from taskflow.domain.entities.task import Task
from taskflow.domain.value_objects.enums import Priority, TaskStatus
from tests.fakes import FakeClock, FakeSignalRepository, FakeTaskRepository, FakeUnitOfWork

NOW = datetime(2026, 8, 4, 10, 0, 0)


def make_uc(fixed_time: datetime = NOW) -> tuple[ScanStaleItemsUseCase, FakeTaskRepository]:
    task_repo = FakeTaskRepository()
    sig_repo = FakeSignalRepository()
    uow = FakeUnitOfWork()
    clock = FakeClock(fixed_time=fixed_time)
    uc = ScanStaleItemsUseCase(
        task_repo=task_repo,
        signal_repo=sig_repo,
        uow=uow,
        clock=clock,
    )
    return uc, task_repo


def make_task(status: TaskStatus, days_old: int = 5) -> Task:
    last = NOW - timedelta(days=days_old)
    return Task(
        id=uuid.uuid4(),
        title="Tarefa teste",
        status=status,
        priority=Priority.MEDIUM,
        last_activity_at=last,
        last_interaction_at=last,
        created_at=last,
        updated_at=last,
    )


class TestScanStaleItems:
    """Testes de varredura de estagnação."""

    @pytest.mark.asyncio
    async def test_waiting_for_4_days_is_stale(self) -> None:
        uc, repo = make_uc()
        task = make_task(TaskStatus.WAITING_ON_OTHERS, days_old=4)
        await repo.save(task)
        result = await uc.execute(ScanStaleItemsCommand(dry_run=True))
        assert result.stale_count == 1

    @pytest.mark.asyncio
    async def test_waiting_for_1_day_is_not_stale(self) -> None:
        uc, repo = make_uc()
        task = make_task(TaskStatus.WAITING_ON_OTHERS, days_old=1)
        await repo.save(task)
        result = await uc.execute(ScanStaleItemsCommand(dry_run=True))
        assert result.stale_count == 0

    @pytest.mark.asyncio
    async def test_dry_run_creates_no_follow_ups(self) -> None:
        uc, repo = make_uc()
        task = make_task(TaskStatus.WAITING_ON_OTHERS, days_old=5)
        await repo.save(task)
        result = await uc.execute(ScanStaleItemsCommand(dry_run=True))
        assert result.follow_ups_created == 0
        assert result.stale_count == 1

    @pytest.mark.asyncio
    async def test_non_dry_run_creates_follow_ups(self) -> None:
        uc, repo = make_uc()
        task = make_task(TaskStatus.WAITING_ON_OTHERS, days_old=5)
        await repo.save(task)
        result = await uc.execute(ScanStaleItemsCommand(dry_run=False))
        assert result.follow_ups_created == 1

    @pytest.mark.asyncio
    async def test_done_task_not_scanned(self) -> None:
        uc, repo = make_uc()
        task = make_task(TaskStatus.DONE, days_old=30)
        await repo.save(task)
        result = await uc.execute(ScanStaleItemsCommand(dry_run=True))
        assert result.stale_count == 0

    @pytest.mark.asyncio
    async def test_in_progress_no_update_7_days_is_stale(self) -> None:
        uc, repo = make_uc()
        task = make_task(TaskStatus.IN_PROGRESS, days_old=8)
        await repo.save(task)
        result = await uc.execute(ScanStaleItemsCommand(dry_run=True))
        assert result.stale_count == 1

    @pytest.mark.asyncio
    async def test_scan_result_contains_task_info(self) -> None:
        uc, repo = make_uc()
        task = make_task(TaskStatus.BLOCKED, days_old=6)
        task.title = "Implementar API de relatórios"
        await repo.save(task)
        result = await uc.execute(ScanStaleItemsCommand(dry_run=True))
        assert result.stale_count >= 1
        report = next(r for r in result.reports if r.task_id == task.id)
        assert report.task_title == "Implementar API de relatórios"
        assert report.stale_reason is not None
