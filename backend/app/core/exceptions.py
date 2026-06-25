"""Global exception handlers.

Without these, an uncaught ValueError, IntegrityError, or any other error
escapes as a generic 500 with a stack trace, leaking internals. These handlers
map them to clean JSON responses with appropriate status codes and log the
detail server-side instead of returning it to the client.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("app")


async def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    # ValueErrors in this app are domain/validation failures with safe messages
    # (e.g. "Already logged for this date"), so a 400 with the message is fine.
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


async def _integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("IntegrityError on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Resource conflict"},
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the global handlers. More specific types win over Exception."""
    app.add_exception_handler(ValueError, _value_error_handler)
    app.add_exception_handler(IntegrityError, _integrity_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
