from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.modules.auth.dependencies import (
    get_current_user,
    require_any_staff,
    require_medical_staff,
    require_admin,
)
from app.modules.patients.service import PatientService
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse
from app.schemas.common import PaginatedResponse, MessageResponse
from app.models.user import User
from fastapi import HTTPException

router = APIRouter()


@router.get(
    "/",
    response_model=PaginatedResponse[PatientResponse],
    summary="Get all patients (paginated)",
)
async def get_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by name, phone or email"),
    current_user: User = Depends(require_any_staff),
    db: AsyncSession = Depends(get_db),
):
    service = PatientService(db)
    patients, total = await service.get_patients(
        current_user=current_user,
        page=page,
        page_size=page_size,
        search=search,
    )
    return PaginatedResponse.create(
        items=patients,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get patient by ID",
)
async def get_patient(
    patient_id: UUID,
    current_user: User = Depends(require_any_staff),
    db: AsyncSession = Depends(get_db),
):
    service = PatientService(db)
    try:
        return await service.get_patient(patient_id, current_user)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new patient",
)
async def create_patient(
    data: PatientCreate,
    current_user: User = Depends(require_any_staff),
    db: AsyncSession = Depends(get_db),
):
    service = PatientService(db)
    return await service.create_patient(data, current_user)


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update patient",
)
async def update_patient(
    patient_id: UUID,
    data: PatientUpdate,
    current_user: User = Depends(require_any_staff),
    db: AsyncSession = Depends(get_db),
):
    service = PatientService(db)
    try:
        return await service.update_patient(patient_id, data, current_user)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete(
    "/{patient_id}",
    response_model=MessageResponse,
    summary="Soft delete patient",
)
async def delete_patient(
    patient_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = PatientService(db)
    try:
        await service.delete_patient(patient_id, current_user)
        return MessageResponse(message="Patient successfully deleted")
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)