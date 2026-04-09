"""
Custom exception classes and FastAPI exception handlers.
All error responses use the shape: { "detail": str, "error_code": str }
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


# ── Custom exception classes ─────────────────────────────────────────────────

class EarthCanvasError(Exception):
    """Base exception for all domain errors."""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class NotFoundError(EarthCanvasError):
    status_code = 404
    error_code = "NOT_FOUND"


class ValidationError(EarthCanvasError):
    status_code = 422
    error_code = "VALIDATION_ERROR"


class ConflictError(EarthCanvasError):
    status_code = 409
    error_code = "CONFLICT"


class BadRequestError(EarthCanvasError):
    status_code = 400
    error_code = "BAD_REQUEST"


# ── Handlers ─────────────────────────────────────────────────────────────────

def _error_body(detail: str, error_code: str) -> dict:
    return {"detail": detail, "error_code": error_code}


async def domain_exception_handler(request: Request, exc: EarthCanvasError):
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.detail, exc.error_code),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    error_code = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_ERROR",
    }.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(str(exc.detail), error_code),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = "; ".join(
        f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}"
        for e in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content=_error_body(messages, "VALIDATION_ERROR"),
    )


def register_exception_handlers(app) -> None:
    app.add_exception_handler(EarthCanvasError, domain_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
