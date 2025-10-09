"""
健康检查控制器
"""

from datetime import datetime

from fastapi import APIRouter

from app.schemas.common import HealthResponse
from config.config import settings

# 创建路由器
router = APIRouter(prefix="/api/health", tags=["健康检查"])


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    健康检查接口

    返回应用的健康状态信息
    """
    return HealthResponse(
        status="healthy",
        version=settings.version,
        timestamp=datetime.utcnow().isoformat(),
    )
