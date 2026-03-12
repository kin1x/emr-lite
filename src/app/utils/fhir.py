import uuid
from datetime import datetime


def generate_fhir_id(prefix: str = "fhir") -> str:
    """Генерирует FHIR-совместимый идентификатор ресурса."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def generate_fhir_resource_id(resource_type: str) -> str:
    """Генерирует FHIR resource ID для медицинской записи."""
    return f"fhir-{resource_type.lower()}-{uuid.uuid4().hex[:12]}"


def to_fhir_date(date) -> str | None:
    """Конвертирует дату в FHIR формат (YYYY-MM-DD)."""
    if date is None:
        return None
    if hasattr(date, "isoformat"):
        return date.isoformat()
    return str(date)


def to_fhir_datetime(dt: datetime) -> str | None:
    """Конвертирует datetime в FHIR формат (ISO 8601)."""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


FHIR_RESOURCE_TYPES = {
    "patient": "Patient",
    "medical_record": "Observation",
    "user": "Practitioner",
}


def get_fhir_resource_type(entity_type: str) -> str:
    """Возвращает FHIR тип ресурса для внутреннего типа сущности."""
    return FHIR_RESOURCE_TYPES.get(entity_type, entity_type.capitalize())