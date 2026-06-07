"""
Material Bin 用户认证 API 主应用
"""

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.controllers import (
    admin_router,
    api_key_router,
    cleanup_router,
    collab_room_router,
    config_router,
    docs_router,
    health_router,
    install_router,
    paste_router,
    user_favorite_router,
    user_history_router,
    user_router,
)
from app.core.error_handlers import register_exception_handlers
from app.core.init_db import create_tables
from app.core.middleware import InstallGateMiddleware
from app.services.install_state_service import ENV_FILE
from config.config import settings, validate_config

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIST_DIR = PROJECT_ROOT / "web" / "dist"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"


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

    if ENV_FILE.exists():
        print("正在检查数据库表...")
        create_tables()
        print("✓ 数据库表检查完成")
    else:
        print("ℹ 未检测到 .env，应用将保持安装待完成状态")

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
    docs_url="/api/openapi/docs" if settings.debug else None,
    redoc_url="/api/openapi/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
)


app.add_middleware(InstallGateMiddleware)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    # Cookie 续期（refresh token）需要 allow_credentials=True 且不能使用 allow_origins=["*"]
    allow_origins=[]
    if settings.debug
    else ["http://localhost:3000"],  # 生产环境需要限制
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
    if settings.debug
    else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(health_router)
app.include_router(config_router)
app.include_router(docs_router)
app.include_router(install_router)
app.include_router(admin_router)
app.include_router(user_router)
app.include_router(api_key_router)
app.include_router(paste_router)
app.include_router(user_favorite_router)
app.include_router(user_history_router)
app.include_router(collab_room_router)
app.include_router(cleanup_router)

# 全局异常处理（避免直接返回 Pydantic 风格错误结构）
register_exception_handlers(app, debug=settings.debug)


def _resolve_frontend_asset(full_path: str) -> Path | None:
    """解析前端构建产物中的静态资源路径，避免目录穿越。"""
    if not FRONTEND_INDEX_FILE.exists() or not full_path:
        return None

    asset_path = (FRONTEND_DIST_DIR / full_path).resolve()
    if asset_path != FRONTEND_DIST_DIR and FRONTEND_DIST_DIR not in asset_path.parents:
        return None
    if asset_path.is_file():
        return asset_path
    return None


# 根路径
@app.get("/", include_in_schema=False)
async def root():
    """根路径欢迎信息"""
    if FRONTEND_INDEX_FILE.exists():
        return FileResponse(FRONTEND_INDEX_FILE)
    return {
        "message": "Welcome to Material Bin User Auth API",
        "version": settings.version,
        "docs": "/api/openapi/docs",
        "health": "/api/health",
    }


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    """在生产部署时托管前端静态文件与 SPA 路由。"""
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="Not Found")

    asset_path = _resolve_frontend_asset(full_path)
    if asset_path is not None:
        return FileResponse(asset_path)

    if not FRONTEND_INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="Not Found")

    if Path(full_path).suffix:
        raise HTTPException(status_code=404, detail="Not Found")

    return FileResponse(FRONTEND_INDEX_FILE)


def run_server():
    """启动服务器"""
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        reload_includes=["*.py", ".env"],
        log_level="debug" if settings.debug else "info",
    )


if __name__ == "__main__":
    run_server()
