import asyncio

import structlog

from taskflow.config.logging import configure_logging

logger = structlog.get_logger()


async def run_worker() -> None:
    """Loop principal do worker de tarefas em segundo plano."""
    configure_logging()
    logger.info("TaskFlow Background Worker iniciado.")
    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info("Worker finalizado com sucesso.")


if __name__ == "__main__":
    asyncio.run(run_worker())
