from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from uuid import UUID
from app.models.medical_record import MedicalRecord, RecordStatus


class MedicalRecordRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, record_id: UUID) -> MedicalRecord | None:
        result = await self.db.execute(
            select(MedicalRecord).where(
                MedicalRecord.id == record_id,
                MedicalRecord.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_relations(self, record_id: UUID) -> MedicalRecord | None:
        result = await self.db.execute(
            select(MedicalRecord)
            .options(
                selectinload(MedicalRecord.patient),
                selectinload(MedicalRecord.doctor),
            )
            .where(
                MedicalRecord.id == record_id,
                MedicalRecord.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        status: RecordStatus | None = None,
    ) -> tuple[list[MedicalRecord], int]:
        query = select(MedicalRecord).where(
            MedicalRecord.deleted_at.is_(None)
        )

        if patient_id:
            query = query.where(MedicalRecord.patient_id == patient_id)
        if doctor_id:
            query = query.where(MedicalRecord.doctor_id == doctor_id)
        if status:
            query = query.where(MedicalRecord.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(MedicalRecord.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        records = result.scalars().all()

        return list(records), total

    async def create(self, record: MedicalRecord) -> MedicalRecord:
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update(self, record: MedicalRecord) -> MedicalRecord:
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def soft_delete(self, record: MedicalRecord) -> None:
        from datetime import datetime, timezone
        record.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()