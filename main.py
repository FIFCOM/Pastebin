"""
Material Bin 用户认证 API 主应用
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.controllers import api_key_router, health_router, paste_router, user_router
from app.core.init_db import init_database
from config.config import settings, validate_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("正在启动 Material Bin...")

    # 验证配置
    try:
        validate_config(settings)
        print("✓ 配置验证通过")
    except RuntimeError as e:
        print(f"✗ 配置验证失败: {e}")
        # 在生产环境中可能需要退出，开发环境中可以继续
        if not settings.debug:
            raise

    # 初始化数据库
    try:
        init_database()
        print("✓ 数据库初始化完成")
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        raise

    print("🚀 应用启动完成")
    yield

    # 关闭时执行
    print("👋 Material Bin已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="基于FastAPI的用户认证模块，支持加密存储和会话管理",
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    if settings.debug
    else ["http://localhost:3000"],  # 生产环境需要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router)
app.include_router(user_router)
app.include_router(api_key_router)
app.include_router(paste_router)


# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """HTTP 异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    """值错误异常处理器"""
    return JSONResponse(
        status_code=400,
        content={
            "error": str(exc),
            "status_code": 400,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """通用异常处理器"""
    error_message = "内部服务器错误"
    if settings.debug:
        error_message = str(exc)

    return JSONResponse(
        status_code=500,
        content={
            "error": error_message,
            "status_code": 500,
        },
    )


# 根路径
@app.get("/")
async def root():
    """根路径欢迎信息"""
    return {
        "message": "Welcome to Material Bin User Auth API",
        "version": settings.version,
        "docs": "/docs",
        "health": "/api/health",
    }


def run_server():
    """启动服务器"""
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )


if __name__ == "__main__":
    run_server()
