import pytest

PATIENT_DATA = {
    "first_name": "Иван",
    "last_name": "Петров",
    "date_of_birth": "1985-03-15",
    "gender": "male",
    "blood_type": "A+",
    "phone": "+79001234567",
}


@pytest.mark.asyncio
async def test_create_patient(client, auth_headers):
    response = await client.post(
        "/api/v1/patients/",
        json=PATIENT_DATA,
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Иван"
    assert data["last_name"] == "Петров"
    assert data["gender"] == "male"
    assert "fhir_id" in data
    assert data["fhir_id"].startswith("fhir-")


@pytest.mark.asyncio
async def test_get_patients_list(client, auth_headers):
    await client.post("/api/v1/patients/", json=PATIENT_DATA, headers=auth_headers)
    response = await client.get("/api/v1/patients/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_patient_by_id(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/patients/",
        json=PATIENT_DATA,
        headers=auth_headers,
    )
    patient_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/patients/{patient_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == patient_id


@pytest.mark.asyncio
async def test_get_patient_not_found(client, auth_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(
        f"/api/v1/patients/{fake_id}",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_patient(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/patients/",
        json=PATIENT_DATA,
        headers=auth_headers,
    )
    patient_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/patients/{patient_id}",
        json={"phone": "+79009999999", "allergies": "Пенициллин"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "+79009999999"
    assert data["allergies"] == "Пенициллин"


@pytest.mark.asyncio
async def test_delete_patient_admin(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/patients/",
        json=PATIENT_DATA,
        headers=auth_headers,
    )
    patient_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/patients/{patient_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Проверяем что пациент недоступен после удаления
    get_resp = await client.get(
        f"/api/v1/patients/{patient_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_patient_forbidden_for_doctor(client, doctor_headers):
    create_resp = await client.post(
        "/api/v1/patients/",
        json=PATIENT_DATA,
        headers=doctor_headers,
    )
    patient_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/patients/{patient_id}",
        headers=doctor_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_search_patients(client, auth_headers):
    await client.post("/api/v1/patients/", json=PATIENT_DATA, headers=auth_headers)
    response = await client.get(
        "/api/v1/patients/?search=Петров",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1