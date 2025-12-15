"""
公开配置控制器 - 返回客户端需要的配置信息
"""

from fastapi import APIRouter
from pydantic import BaseModel

from config.config import settings

router = APIRouter(prefix="/api/config", tags=["配置"])


class PublicConfig(BaseModel):
    """客户端公开配置"""
    max_upload_file_size: int
    max_chunk_size: int


@router.get("", response_model=PublicConfig)
async def get_public_config():
    """
    获取客户端公开配置

    返回文件上传限制等客户端需要的配置信息
    """
    return PublicConfig(
        max_upload_file_size=settings.max_upload_file_size,
        max_chunk_size=settings.max_chunk_size,
    )
