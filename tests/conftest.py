import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.database import Base, get_db
from app.core.redis import redis_client

TEST_DATABASE_URL = "postgresql+asyncpg://emr_user:emr_password@postgres:5432/emr_test"

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class MockRedis:
    def __init__(self):
        self._store = {}

    async def connect(self): pass
    async def disconnect(self): pass
    async def get(self, key: str):
        return self._store.get(key)
    async def set(self, key: str, value: str, expire: int = None):
        self._store[key] = value
    async def delete(self, key: str):
        self._store.pop(key, None)
    async def exists(self, key: str) -> bool:
        return key in self._store

    @property
    def client(self):
        return self


@pytest.fixture(scope="session")
def mock_redis():
    return MockRedis()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session, mock_redis, monkeypatch):
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.core.redis.redis_client", mock_redis)
    monkeypatch.setattr("app.modules.auth.service.redis_client", mock_redis)
    monkeypatch.setattr("app.modules.auth.dependencies.redis_client", mock_redis)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "admin@test.com",
        "password": "Admin123",
        "first_name": "Admin",
        "last_name": "Test",
        "role": "admin",
    })
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def doctor_user(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "doctor@test.com",
        "password": "Doctor123",
        "first_name": "Doctor",
        "last_name": "Test",
        "role": "doctor",
    })
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def admin_token(client, admin_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "Admin123",
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def doctor_token(client, doctor_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "doctor@test.com",
        "password": "Doctor123",
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def doctor_headers(doctor_token):
    return {"Authorization": f"Bearer {doctor_token}"}
