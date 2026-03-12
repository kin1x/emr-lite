from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import redis_client
from app.core.logging import setup_logging, logger
from app.core.exceptions import EMRException
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info("Starting EMR-Lite", version=settings.APP_VERSION, env=settings.APP_ENV)

    # Подключаем Redis
    await redis_client.connect()
    logger.info("Redis connected")

    # Создаём таблицы (в продакшене — через Alembic миграции)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")

    yield

    # Shutdown
    await redis_client.disconnect()
    await engine.dispose()
    logger.info("EMR-Lite shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
## EMR-Lite - Electronic Medical Records System

Система управления медицинскими записями с поддержкой FHIR R4.

### Возможности
Аутентификация - JWT access/refresh токены
RBAC - роли: admin, doctor, nurse, receptionist, patient
Пациенты - полное управление профилями
Медицинские записи - с ICD-10 кодами и FHIR совместимостью
Audit Log - полное логирование всех действий
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Глобальный обработчик кастомных исключений
    @app.exception_handler(EMRException)
    async def emr_exception_handler(request: Request, exc: EMRException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    # Глобальный обработчик непредвиденных ошибок
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # Подключаем роутеры
    app.include_router(api_router)

    # Health check
    @app.get("/health", tags=["System"], summary="Health check")
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
        }

    @app.get("/", tags=["System"], include_in_schema=False)
    async def root():
        return {"message": f"Welcome to {settings.APP_NAME}", "docs": "/docs"}

    return app


app = create_app()