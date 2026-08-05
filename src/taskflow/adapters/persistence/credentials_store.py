from sqlalchemy import select

from taskflow.adapters.persistence.models import CredentialORM
from taskflow.config.container import SessionLocal


async def save_credential(key: str, value: str) -> None:
    """Salva ou atualiza uma credencial no banco de dados."""
    async with SessionLocal() as session:
        result = await session.execute(select(CredentialORM).where(CredentialORM.key == key))
        cred = result.scalar_one_or_none()
        
        if cred:
            cred.value = value
        else:
            cred = CredentialORM(key=key, value=value)
            session.add(cred)
            
        await session.commit()

async def get_credential(key: str) -> str | None:
    """Recupera uma credencial do banco de dados."""
    async with SessionLocal() as session:
        result = await session.execute(select(CredentialORM).where(CredentialORM.key == key))
        cred = result.scalar_one_or_none()
        
        return cred.value if cred else None
