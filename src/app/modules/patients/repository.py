from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from uuid import UUID
from app.models.patient import Patient


class PatientRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, patient_id: UUID) -> Patient | None:
        result = await self.db.execute(
            select(Patient).where(
                Patient.id == patient_id,
                Patient.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_fhir_id(self, fhir_id: str) -> Patient | None:
        result = await self.db.execute(
            select(Patient).where(
                Patient.fhir_id == fhir_id,
                Patient.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> tuple[list[Patient], int]:
        query = select(Patient).where(Patient.deleted_at.is_(None))

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Patient.first_name.ilike(search_term),
                    Patient.last_name.ilike(search_term),
                    Patient.phone.ilike(search_term),
                    Patient.email.ilike(search_term),
                )
            )

        # Считаем total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Получаем страницу
        query = query.order_by(Patient.last_name, Patient.first_name)
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        patients = result.scalars().all()

        return list(patients), total

    async def create(self, patient: Patient) -> Patient:
        self.db.add(patient)
        await self.db.flush()
        await self.db.refresh(patient)
        return patient

    async def update(self, patient: Patient) -> Patient:
        await self.db.flush()
        await self.db.refresh(patient)
        return patient

    async def soft_delete(self, patient: Patient) -> None:
        from datetime import datetime, timezone
        patient.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()