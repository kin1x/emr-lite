from typing import Any
from fastapi import HTTPException, status


class EMRException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(EMRException):
    def __init__(self, resource: str, resource_id: Any = None):
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} with id '{resource_id}' not found"
        super().__init__(msg, status_code=404)


class PermissionDeniedException(EMRException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)


class AlreadyExistsException(EMRException):
    def __init__(self, resource: str):
        super().__init__(f"{resource} already exists", status_code=409)


class UnauthorizedException(EMRException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


# FastAPI HTTP exceptions shortcuts
def http_404(detail: str = "Not found"):
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def http_403(detail: str = "Permission denied"):
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def http_401(detail: str = "Unauthorized"):
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def http_409(detail: str = "Already exists"):
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)