from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medical_record import MedicalRecord, RecordStatus
from app.models.user import User, UserRole
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate
from app.modules.records.repository import MedicalRecordRepository
from app.modules.patients.repository import PatientRepository
from app.modules.audit.service import AuditService
from app.models.audit_log import AuditAction
from app.core.exceptions import (
    EMRException,
    NotFoundException,
    PermissionDeniedException,
)


class MedicalRecordService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MedicalRecordRepository(db)
        self.patient_repo = PatientRepository(db)
        self.audit = AuditService(db)

    async def get_record(
        self, record_id: UUID, current_user: User
    ) -> MedicalRecord:
        record = await self.repo.get_by_id_with_relations(record_id)
        if not record:
            raise NotFoundException("MedicalRecord", record_id)

        await self.audit.log(
            user=current_user,
            action=AuditAction.READ,
            resource_type="medical_record",
            resource_id=str(record_id),
        )
        return record

    async def get_records(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        status: RecordStatus | None = None,
    ) -> tuple[list[MedicalRecord], int]:
        offset = (page - 1) * page_size

        # Врач видит только свои записи если не admin
        if current_user.role == UserRole.DOCTOR:
            doctor_id = current_user.id

        return await self.repo.get_all(
            offset=offset,
            limit=page_size,
            patient_id=patient_id,
            doctor_id=doctor_id,
            status=status,
        )

    async def create_record(
        self, data: MedicalRecordCreate, current_user: User
    ) -> MedicalRecord:
        # Проверяем что пациент существует
        patient = await self.patient_repo.get_by_id(data.patient_id)
        if not patient:
            raise NotFoundException("Patient", data.patient_id)

        record = MedicalRecord(
            patient_id=data.patient_id,
            doctor_id=current_user.id,
            record_type=data.record_type,
            title=data.title,
            description=data.description,
            icd_code=data.icd_code,
            metadata_json=data.metadata_json,
            status=RecordStatus.DRAFT,
            fhir_resource_id=f"fhir-rec-{uuid4().hex[:12]}",
        )
        record = await self.repo.create(record)

        await self.audit.log(
            user=current_user,
            action=AuditAction.CREATE,
            resource_type="medical_record",
            resource_id=str(record.id),
            description=f"Created {record.record_type} record for patient {data.patient_id}",
        )
        return record

    async def update_record(
        self,
        record_id: UUID,
        data: MedicalRecordUpdate,
        current_user: User,
    ) -> MedicalRecord:
        record = await self.repo.get_by_id(record_id)
        if not record:
            raise NotFoundException("MedicalRecord", record_id)

        # Только автор или admin может редактировать
        if (
            current_user.role != UserRole.ADMIN
            and record.doctor_id != current_user.id
        ):
            raise PermissionDeniedException(
                "Only the author or admin can edit this record"
            )

        # Нельзя редактировать финальную запись
        if record.status == RecordStatus.FINAL and data.status != RecordStatus.AMENDED:
            raise EMRException(
                "Cannot edit a finalized record. Set status to 'amended' first",
                status_code=400
            )

        update_data = data.model_dump(exclude_unset=True)
        old_values = {k: str(getattr(record, k)) for k in update_data}

        for field, value in update_data.items():
            setattr(record, field, value)

        record = await self.repo.update(record)

        await self.audit.log(
            user=current_user,
            action=AuditAction.UPDATE,
            resource_type="medical_record",
            resource_id=str(record_id),
            changes={"before": old_values, "after": {k: str(v) for k, v in update_data.items()}},
        )
        return record

    async def delete_record(
        self, record_id: UUID, current_user: User
    ) -> None:
        record = await self.repo.get_by_id(record_id)
        if not record:
            raise NotFoundException("MedicalRecord", record_id)

        if current_user.role != UserRole.ADMIN:
            raise PermissionDeniedException("Only admin can delete records")

        await self.repo.soft_delete(record)

        await self.audit.log(
            user=current_user,
            action=AuditAction.DELETE,
            resource_type="medical_record",
            resource_id=str(record_id),
        )