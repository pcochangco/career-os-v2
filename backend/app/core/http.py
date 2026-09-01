from __future__ import annotations

import json
import logging
import re
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from app.core.config import Settings

# Uvicorn configures this logger with an INFO-level production handler. Reusing
# it keeps request events visible without adding a second, duplicate handler.
logger = logging.getLogger("uvicorn.error")

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def request_id_from(request: Request) -> str:
    supplied = request.headers.get("X-Request-ID", "")
    if REQUEST_ID_PATTERN.fullmatch(supplied):
        return supplied
    return uuid4().hex


def add_http_middleware(application: FastAPI, settings: Settings) -> None:
    @application.middleware("http")
    async def secure_and_trace(request: Request, call_next) -> Response:
        request_id = request_id_from(request)
        request.state.request_id = request_id
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            duration_ms = round((perf_counter() - started) * 1000)
            logger.exception(
                json.dumps(
                    {
                        "duration_ms": duration_ms,
                        "event": "http_request_failed",
                        "method": request.method,
                        "path": request.url.path,
                        "request_id": request_id,
                        "status_code": status_code,
                    },
                    separators=(",", ":"),
                )
            )
            raise

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        if settings.environment.lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        if request.url.path != "/api/v1/health":
            logger.info(
                json.dumps(
                    {
                        "duration_ms": round((perf_counter() - started) * 1000),
                        "event": "http_request_completed",
                        "method": request.method,
                        "path": request.url.path,
                        "request_id": request_id,
                        "status_code": status_code,
                    },
                    separators=(",", ":"),
                )
            )
        return response
