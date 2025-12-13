"""
Global exception handlers.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.requests import Request


def _validation_errors_to_simple_list(errors: Sequence[Any]) -> list[dict[str, str]]:
    """
    Convert FastAPI/Pydantic validation errors into a stable, frontend-friendly list.
    Avoid leaking the full Pydantic error payload (ctx/input/url...).
    """

    def loc_to_field(loc: object) -> str:
        if not isinstance(loc, (tuple, list)):
            return ""
        parts: list[str] = []
        for item in loc:
            # FastAPI prefixes like: ("body", "email") / ("query", "page")
            if item in {"body", "query", "path", "header", "cookie"}:
                continue
            if isinstance(item, int):
                # attach list index to the previous key if possible
                if parts:
                    parts[-1] = f"{parts[-1]}[{item}]"
                else:
                    parts.append(f"[{item}]")
                continue
            parts.append(str(item))
        return ".".join(parts)

    simplified: list[dict[str, str]] = []
    for err in errors:
        loc = err.get("loc", ())
        field = loc_to_field(loc)
        msg = str(err.get("msg", "Invalid value"))
        simplified.append({"field": field, "message": msg})
    return simplified


def _validation_detail_message(simple_errors: list[dict[str, str]]) -> str:
    if not simple_errors:
        return "请求参数校验失败"
    first = simple_errors[0]
    head = (
        f"{first['field']}: {first['message']}"
        if first.get("field")
        else first.get("message", "请求参数校验失败")
    )
    if len(simple_errors) == 1:
        return head
    return f"{head}（等{len(simple_errors)}处）"


def register_exception_handlers(app: FastAPI, *, debug: bool) -> None:
    """
    Register exception handlers to avoid leaking raw Pydantic error payloads to clients.
    """

    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        simple_errors = _validation_errors_to_simple_list(exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "error": "请求参数校验失败",
                # Keep `detail` a string (avoid FastAPI/Pydantic default list payload)
                "detail": _validation_detail_message(simple_errors),
                "errors": simple_errors,
                "status_code": 422,
            },
        )

    async def pydantic_validation_exception_handler(
        request: Request, exc: ValidationError
    ):
        simple_errors = _validation_errors_to_simple_list(exc.errors())
        return JSONResponse(
            status_code=400,
            content={
                "error": "数据校验失败",
                "detail": _validation_detail_message(simple_errors),
                "errors": simple_errors,
                "status_code": 400,
            },
        )

    async def response_validation_exception_handler(
        request: Request, exc: ResponseValidationError
    ):
        simple_errors = _validation_errors_to_simple_list(exc.errors())
        return JSONResponse(
            status_code=500,
            content={
                "error": "响应数据校验失败",
                "detail": _validation_detail_message(simple_errors),
                "errors": simple_errors,
                "status_code": 500,
            },
        )

    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "detail": exc.detail,
                "status_code": exc.status_code,
            },
        )

    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={
                "error": str(exc),
                "detail": str(exc),
                "status_code": 400,
            },
        )

    async def general_exception_handler(request: Request, exc: Exception):
        error_message = str(exc) if debug else "内部服务器错误"
        return JSONResponse(
            status_code=500,
            content={
                "error": error_message,
                "detail": error_message,
                "status_code": 500,
            },
        )

    app.add_exception_handler(
        RequestValidationError, request_validation_exception_handler  # type: ignore[arg-type]
    )
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(
        ResponseValidationError, response_validation_exception_handler  # type: ignore[arg-type]
    )
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValueError, value_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, general_exception_handler)  # type: ignore[arg-type]
