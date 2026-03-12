from typing import TypeVar, Generic, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

T = TypeVar("T")


def paginate(query, page: int, page_size: int):
    """Применяет пагинацию к SQLAlchemy запросу."""
    return query.offset((page - 1) * page_size).limit(page_size)


async def get_total_count(db: AsyncSession, query) -> int:
    """Возвращает общее количество записей для запроса."""
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    return result.scalar_one()