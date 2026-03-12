import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@test.com",
        "password": "NewUser123",
        "first_name": "New",
        "last_name": "User",
        "role": "doctor",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["role"] == "doctor"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {
        "email": "duplicate@test.com",
        "password": "Test1234",
        "first_name": "Test",
        "last_name": "User",
        "role": "nurse",
    }
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "weak@test.com",
        "password": "weak",
        "first_name": "Weak",
        "last_name": "Pass",
        "role": "nurse",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "Admin123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "WrongPass123",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client, auth_headers):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_logout(client, admin_token, auth_headers):
    response = await client.post(
        "/api/v1/auth/logout",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"