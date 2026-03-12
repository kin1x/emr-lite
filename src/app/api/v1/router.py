from fastapi import APIRouter
from app.modules.auth.router import router as auth_router
from app.modules.patients.router import router as patients_router
from app.modules.records.router import router as records_router
from app.modules.audit.router import router as audit_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(patients_router, prefix="/patients", tags=["Patients"])
api_router.include_router(records_router, prefix="/records", tags=["Medical Records"])
api_router.include_router(audit_router, prefix="/audit", tags=["Audit Logs"])