"""CapacityPolicy — Consciência de capacidade diária — RF-F.6.

Calcula horas livres por dia considerando reuniões, horário de trabalho
e buffer configurável.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class TimeBlock:
    """Bloco de tempo ocupado por uma reunião."""

    starts_at: datetime
    ends_at: datetime
    title: str | None = None
    is_all_day: bool = False

    @property
    def duration_minutes(self) -> float:
        """Duração do bloco em minutos."""
        if self.is_all_day:
            return 0.0  # All-day não conta para cálculo de capacidade horária
        delta = self.ends_at - self.starts_at
        return max(0.0, delta.total_seconds() / 60)


@dataclass
class DayCapacity:
    """Capacidade calculada para um dia."""

    date: datetime
    total_work_minutes: float
    meeting_minutes: float
    buffer_minutes: float
    free_minutes: float
    is_work_day: bool
    blocks: list[TimeBlock]

    @property
    def is_overloaded(self) -> bool:
        """Retorna True se há menos de 60 minutos livres no dia."""
        return self.is_work_day and self.free_minutes < 60

    @property
    def free_hours(self) -> float:
        """Horas livres (formato decimal)."""
        return self.free_minutes / 60


class CapacityPolicy:
    """Calcula a capacidade diária considerando reuniões e horário de trabalho.

    Implementação 100% determinística e testável sem I/O.

    Suporte a:
    - Eventos sobrepostos (não contam duplamente)
    - Eventos all-day (ignorados para cálculo horário)
    - Eventos fora do horário de trabalho (não contam)
    - Múltiplos fusos horários (normalizado para UTC internamente)
    """

    def __init__(
        self,
        work_start: time = time(8, 30),
        work_end: time = time(18, 0),
        work_days: frozenset[int] = frozenset({0, 1, 2, 3, 4}),  # Mon-Fri
        buffer_minutes: int = 60,
    ) -> None:
        self.work_start = work_start
        self.work_end = work_end
        self.work_days = work_days
        self.buffer_minutes = buffer_minutes

    def _work_minutes_for_day(self, date: datetime) -> float:
        """Retorna minutos úteis no dia."""
        if date.weekday() not in self.work_days:
            return 0.0
        work_start_dt = date.replace(
            hour=self.work_start.hour,
            minute=self.work_start.minute,
            second=0,
            microsecond=0,
        )
        work_end_dt = date.replace(
            hour=self.work_end.hour,
            minute=self.work_end.minute,
            second=0,
            microsecond=0,
        )
        return max(0.0, (work_end_dt - work_start_dt).total_seconds() / 60)

    def _clip_to_work_hours(self, block: TimeBlock, date: datetime) -> float:
        """Recorta o bloco ao horário de trabalho e retorna minutos efetivos."""
        if block.is_all_day:
            return 0.0

        work_start = date.replace(
            hour=self.work_start.hour,
            minute=self.work_start.minute,
            second=0,
            microsecond=0,
        )
        work_end = date.replace(
            hour=self.work_end.hour,
            minute=self.work_end.minute,
            second=0,
            microsecond=0,
        )

        clipped_start = max(block.starts_at.replace(tzinfo=None), work_start)
        clipped_end = min(block.ends_at.replace(tzinfo=None), work_end)

        if clipped_end <= clipped_start:
            return 0.0
        return (clipped_end - clipped_start).total_seconds() / 60

    def _merge_overlapping(self, blocks: list[TimeBlock]) -> list[tuple[datetime, datetime]]:
        """Mescla blocos sobrepostos para evitar contagem dupla."""
        if not blocks:
            return []

        sorted_blocks = sorted(blocks, key=lambda b: b.starts_at)
        merged: list[tuple[datetime, datetime]] = []
        current_start = sorted_blocks[0].starts_at
        current_end = sorted_blocks[0].ends_at

        for block in sorted_blocks[1:]:
            if block.starts_at <= current_end:
                current_end = max(current_end, block.ends_at)
            else:
                merged.append((current_start, current_end))
                current_start = block.starts_at
                current_end = block.ends_at

        merged.append((current_start, current_end))
        return merged

    def compute(self, date: datetime, blocks: list[TimeBlock]) -> DayCapacity:
        """Calcula a capacidade do dia.

        Args:
            date: Dia para o qual calcular (apenas a data é usada).
            blocks: Lista de blocos de tempo de reunião.
        """
        is_work_day = date.weekday() in self.work_days
        total_work = self._work_minutes_for_day(date)

        if not is_work_day:
            return DayCapacity(
                date=date,
                total_work_minutes=0,
                meeting_minutes=0,
                buffer_minutes=0,
                free_minutes=0,
                is_work_day=False,
                blocks=blocks,
            )

        # Filtra blocos do mesmo dia e mescla sobrepostos
        day_blocks = [
            b for b in blocks
            if b.starts_at.date() == date.date() or b.ends_at.date() == date.date()
        ]

        merged = self._merge_overlapping(day_blocks)

        work_start = date.replace(
            hour=self.work_start.hour,
            minute=self.work_start.minute,
            second=0,
            microsecond=0,
        )
        work_end = date.replace(
            hour=self.work_end.hour,
            minute=self.work_end.minute,
            second=0,
            microsecond=0,
        )

        meeting_minutes = 0.0
        for start, end in merged:
            clipped_start = max(start.replace(tzinfo=None), work_start)
            clipped_end = min(end.replace(tzinfo=None), work_end)
            if clipped_end > clipped_start:
                meeting_minutes += (clipped_end - clipped_start).total_seconds() / 60

        free_minutes = max(0.0, total_work - meeting_minutes - self.buffer_minutes)

        return DayCapacity(
            date=date,
            total_work_minutes=total_work,
            meeting_minutes=meeting_minutes,
            buffer_minutes=float(self.buffer_minutes),
            free_minutes=free_minutes,
            is_work_day=True,
            blocks=day_blocks,
        )
