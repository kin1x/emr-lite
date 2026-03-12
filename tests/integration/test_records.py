import pytest

PATIENT_DATA = {
    "first_name": "Тест",
    "last_name": "Пациент",
    "date_of_birth": "1990-01-01",
    "gender": "male",
    "blood_type": "A+",
    "phone": "+79009876543",
}

RECORD_DATA = {
    "record_type": "consultation",
    "title": "Первичный осмотр",
    "description": "Жалобы на головную боль",
    "icd_code": "R51",
}


@pytest.fixture
async def patient(client, auth_headers):
    response = await client.post(
        "/api/v1/patients/",
        json=PATIENT_DATA,
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_create_record(client, auth_headers, patient):
    response = await client.post(
        "/api/v1/records/",
        json={**RECORD_DATA, "patient_id": patient["id"]},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["record_type"] == "consultation"
    assert data["status"] == "draft"
    assert data["icd_code"] == "R51"
    assert "fhir_resource_id" in data
    assert data["fhir_resource_id"].startswith("fhir-")


@pytest.mark.asyncio
async def test_get_records_list(client, auth_headers, patient):
    await client.post(
        "/api/v1/records/",
        json={**RECORD_DATA, "patient_id": patient["id"]},
        headers=auth_headers,
    )
    response = await client.get("/api/v1/records/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_record_by_id(client, auth_headers, patient):
    create_resp = await client.post(
        "/api/v1/records/",
        json={**RECORD_DATA, "patient_id": patient["id"]},
        headers=auth_headers,
    )
    record_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/records/{record_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == record_id


@pytest.mark.asyncio
async def test_get_record_not_found(client, auth_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(
        f"/api/v1/records/{fake_id}",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_record(client, auth_headers, patient):
    create_resp = await client.post(
        "/api/v1/records/",
        json={**RECORD_DATA, "patient_id": patient["id"]},
        headers=auth_headers,
    )
    record_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/records/{record_id}",
        json={"description": "Обновлённое описание", "icd_code": "G43.0"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Обновлённое описание"
    assert data["icd_code"] == "G43.0"


@pytest.mark.asyncio
async def test_finalize_record(client, auth_headers, patient):
    create_resp = await client.post(
        "/api/v1/records/",
        json={**RECORD_DATA, "patient_id": patient["id"]},
        headers=auth_headers,
    )
    record_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/records/{record_id}/finalize",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "final"


@pytest.mark.asyncio
async def test_cannot_edit_final_record(client, auth_headers, patient):
    create_resp = await client.post(
        "/api/v1/records/",
        json={**RECORD_DATA, "patient_id": patient["id"]},
        headers=auth_headers,
    )
    record_id = create_resp.json()["id"]

    await client.patch(
        f"/api/v1/records/{record_id}/finalize",
        headers=auth_headers,
    )

    response = await client.patch(
        f"/api/v1/records/{record_id}",
        json={"description": "Попытка изменить финальную запись"},
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_record_admin(client, auth_headers, patient):
    create_resp = await client.post(
        "/api/v1/records/",
        json={**RECORD_DATA, "patient_id": patient["id"]},
        headers=auth_headers,
    )
    record_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/records/{record_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200

    get_resp = await client.get(
        f"/api/v1/records/{record_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_doctor_sees_only_own_records(client, doctor_headers, auth_headers, patient):
    # Admin создаёт запись
    await client.post(
        "/api/v1/records/",
        json={**RECORD_DATA, "patient_id": patient["id"]},
        headers=auth_headers,
    )

    # Doctor видит только свои (должно быть 0)
    response = await client.get("/api/v1/records/", headers=doctor_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_filter_records_by_patient(client, auth_headers, patient):
    await client.post(
        "/api/v1/records/",
        json={**RECORD_DATA, "patient_id": patient["id"]},
        headers=auth_headers,
    )
    response = await client.get(
        f"/api/v1/records/?patient_id={patient['id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["patient_id"] == patient["id"]