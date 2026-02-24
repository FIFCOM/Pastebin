"""
安装状态拦截中间件
"""

import asyncio

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import SessionLocal
from app.services.install_state_service import (
    ENV_FILE,
    InstallState,
    InstallStateService,
)


def _is_install_gate_whitelisted(path: str) -> bool:
    if path in {"/api/install", "/api/health", "/api/health/", "/openapi.json"}:
        return True
    return (
        path.startswith("/api/install/")
        or path.startswith("/docs")
        or path.startswith("/redoc")
    )


class InstallGateMiddleware(BaseHTTPMiddleware):
    @staticmethod
    def _load_install_state() -> InstallState:
        db = SessionLocal()
        try:
            return InstallStateService.get_state(db)
        finally:
            db.close()

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        request_path = request.url.path
        if _is_install_gate_whitelisted(request_path):
            return await call_next(request)

        if not ENV_FILE.exists():
            needs_install = True
        else:
            install_state = await asyncio.to_thread(self._load_install_state)
            needs_install = install_state.needs_install

        if needs_install:
            return JSONResponse(
                status_code=428,
                content={
                    "error": "安装未完成",
                    "detail": "安装未完成，请先完成安装",
                    "status_code": 428,
                    "code": "INSTALL_REQUIRED",
                },
            )

        return await call_next(request)
