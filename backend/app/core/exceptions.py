from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_422_UNPROCESSABLE_CONTENT


def _serialize_detail(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return "; ".join(str(item) for item in detail)
    return str(detail)


def _error_payload(message: str, detail: Any) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "detail": _serialize_detail(detail),
    }


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code == HTTP_401_UNAUTHORIZED:
        message = "Unauthorized"
    elif exc.status_code == HTTP_403_FORBIDDEN:
        message = "Permission denied"
    else:
        message = "Error"

    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(message, exc.detail),
        headers=getattr(exc, "headers", None) or {},
    )


async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    detail = "; ".join(
        f"{'/'.join(str(loc) for loc in error.get('loc', []))}: {error.get('msg')}"
        for error in exc.errors()
    )
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_CONTENT,
        content=_error_payload("Validation error", detail),
    )
