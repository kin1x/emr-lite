from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from app.models.medical_record import RecordType, RecordStatus
from app.schemas.user import UserShortResponse
from app.schemas.patient import PatientShortResponse


class MedicalRecordBase(BaseModel):
    record_type: RecordType
    title: str
    description: Optional[str] = None
    icd_code: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class MedicalRecordCreate(MedicalRecordBase):
    patient_id: UUID


class MedicalRecordUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[RecordStatus] = None
    icd_code: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class MedicalRecordResponse(MedicalRecordBase):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    status: RecordStatus
    fhir_resource_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MedicalRecordDetailResponse(MedicalRecordResponse):
    patient: PatientShortResponse
    doctor: UserShortResponse

    model_config = {"from_attributes": True}