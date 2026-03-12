import uuid
from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.core.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class RecordType(str, enum.Enum):
    CONSULTATION = "consultation"
    DIAGNOSIS = "diagnosis"
    PRESCRIPTION = "prescription"
    LAB_RESULT = "lab_result"
    IMAGING = "imaging"
    DISCHARGE = "discharge"
    REFERRAL = "referral"


class RecordStatus(str, enum.Enum):
    DRAFT = "draft"
    FINAL = "final"
    AMENDED = "amended"
    CANCELLED = "cancelled"


class MedicalRecord(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "medical_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    record_type: Mapped[RecordType] = mapped_column(
        SAEnum(RecordType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status: Mapped[RecordStatus] = mapped_column(
        SAEnum(RecordStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RecordStatus.DRAFT,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icd_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fhir_resource_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True
    )

    patient: Mapped["Patient"] = relationship(
        "Patient", back_populates="medical_records", lazy="noload"
    )
    doctor: Mapped["User"] = relationship("User", lazy="noload")