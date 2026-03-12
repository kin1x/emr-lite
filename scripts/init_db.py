#!/usr/bin/env python3
"""
Скрипт инициализации базы данных.
Создаёт все таблицы через SQLAlchemy (альтернатива Alembic для dev).

Использование:
    python scripts/init_db.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app.core.database import engine, Base
from app.core.logging import setup_logging, logger
import app.models  # noqa: F401 — регистрируем все модели


async def init_db():
    setup_logging()
    logger.info("Initializing database...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())