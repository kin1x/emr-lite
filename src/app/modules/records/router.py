from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.exceptions import NotFoundException, PermissionDeniedException
from app.modules.auth.dependencies import (
    get_current_user,
    require_medical_staff,
    require_admin,
)
from app.modules.records.service import MedicalRecordService
from app.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordUpdate,
    MedicalRecordResponse,
    MedicalRecordDetailResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.models.medical_record import RecordStatus
from app.models.user import User

router = APIRouter()


@router.get(
    "/",
    response_model=PaginatedResponse[MedicalRecordResponse],
    summary="Get all medical records (paginated)",
)
async def get_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    patient_id: UUID | None = Query(None),
    doctor_id: UUID | None = Query(None),
    status: RecordStatus | None = Query(None),
    current_user: User = Depends(require_medical_staff),
    db: AsyncSession = Depends(get_db),
):
    service = MedicalRecordService(db)
    records, total = await service.get_records(
        current_user=current_user,
        page=page,
        page_size=page_size,
        patient_id=patient_id,
        doctor_id=doctor_id,
        status=status,
    )
    return PaginatedResponse.create(
        items=records,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{record_id}",
    response_model=MedicalRecordDetailResponse,
    summary="Get medical record by ID with patient and doctor details",
)
async def get_record(
    record_id: UUID,
    current_user: User = Depends(require_medical_staff),
    db: AsyncSession = Depends(get_db),
):
    service = MedicalRecordService(db)
    try:
        return await service.get_record(record_id, current_user)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new medical record",
)
async def create_record(
    data: MedicalRecordCreate,
    current_user: User = Depends(require_medical_staff),
    db: AsyncSession = Depends(get_db),
):
    service = MedicalRecordService(db)
    try:
        return await service.create_record(data, current_user)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.patch(
    "/{record_id}",
    response_model=MedicalRecordResponse,
    summary="Update medical record",
)
async def update_record(
    record_id: UUID,
    data: MedicalRecordUpdate,
    current_user: User = Depends(require_medical_staff),
    db: AsyncSession = Depends(get_db),
):
    service = MedicalRecordService(db)
    try:
        return await service.update_record(record_id, data, current_user)
    except (NotFoundException, PermissionDeniedException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.patch(
    "/{record_id}/finalize",
    response_model=MedicalRecordResponse,
    summary="Finalize medical record (set status to FINAL)",
)
async def finalize_record(
    record_id: UUID,
    current_user: User = Depends(require_medical_staff),
    db: AsyncSession = Depends(get_db),
):
    service = MedicalRecordService(db)
    try:
        return await service.update_record(
            record_id,
            MedicalRecordUpdate(status=RecordStatus.FINAL),
            current_user,
        )
    except (NotFoundException, PermissionDeniedException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete(
    "/{record_id}",
    response_model=MessageResponse,
    summary="Soft delete medical record (admin only)",
)
async def delete_record(
    record_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = MedicalRecordService(db)
    try:
        await service.delete_record(record_id, current_user)
        return MessageResponse(message="Medical record successfully deleted")
    except (NotFoundException, PermissionDeniedException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)