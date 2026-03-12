from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from app.models.audit_log import AuditAction


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    action: AuditAction
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    changes: Optional[dict[str, Any]] = None
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogFilter(BaseModel):
    user_id: Optional[UUID] = None
    action: Optional[AuditAction] = None
    resource_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None