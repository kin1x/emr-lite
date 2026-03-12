from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import PatientCreate, PatientUpdate
from app.modules.patients.repository import PatientRepository
from app.modules.audit.service import AuditService
from app.models.audit_log import AuditAction
from app.core.exceptions import NotFoundException, PermissionDeniedException


class PatientService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PatientRepository(db)
        self.audit = AuditService(db)

    async def get_patient(self, patient_id: UUID, current_user: User) -> Patient:
        patient = await self.repo.get_by_id(patient_id)
        if not patient:
            raise NotFoundException("Patient", patient_id)

        await self.audit.log(
            user=current_user,
            action=AuditAction.READ,
            resource_type="patient",
            resource_id=str(patient_id),
        )
        return patient

    async def get_patients(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[Patient], int]:
        offset = (page - 1) * page_size
        patients, total = await self.repo.get_all(
            offset=offset,
            limit=page_size,
            search=search,
        )
        return patients, total

    async def create_patient(
        self, data: PatientCreate, current_user: User
    ) -> Patient:
        patient = Patient(
            **data.model_dump(),
            fhir_id=f"fhir-{uuid4().hex[:12]}",
        )
        patient = await self.repo.create(patient)

        await self.audit.log(
            user=current_user,
            action=AuditAction.CREATE,
            resource_type="patient",
            resource_id=str(patient.id),
            description=f"Created patient: {patient.last_name} {patient.first_name}",
        )
        return patient

    async def update_patient(
        self,
        patient_id: UUID,
        data: PatientUpdate,
        current_user: User,
    ) -> Patient:
        patient = await self.repo.get_by_id(patient_id)
        if not patient:
            raise NotFoundException("Patient", patient_id)

        update_data = data.model_dump(exclude_unset=True)
        old_values = {k: getattr(patient, k) for k in update_data}

        for field, value in update_data.items():
            setattr(patient, field, value)

        patient = await self.repo.update(patient)

        await self.audit.log(
            user=current_user,
            action=AuditAction.UPDATE,
            resource_type="patient",
            resource_id=str(patient_id),
            changes={"before": str(old_values), "after": str(update_data)},
        )
        return patient

    async def delete_patient(
        self, patient_id: UUID, current_user: User
    ) -> None:
        patient = await self.repo.get_by_id(patient_id)
        if not patient:
            raise NotFoundException("Patient", patient_id)

        await self.repo.soft_delete(patient)

        await self.audit.log(
            user=current_user,
            action=AuditAction.DELETE,
            resource_type="patient",
            resource_id=str(patient_id),
            description=f"Soft deleted patient: {patient.last_name} {patient.first_name}",
        )