from __future__ import annotations

from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.domain.ports.ports import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Implementação da UnitOfWork do SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        if args and args[0] is not None:
            await self.rollback()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
