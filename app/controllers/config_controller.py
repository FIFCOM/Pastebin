"""
公开配置控制器 - 返回客户端需要的配置信息
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.email_settings_service import EmailSettingsService
from app.services.runtime_settings_service import RuntimeSettingsService

router = APIRouter(prefix="/api/config", tags=["配置"])


class PublicConfig(BaseModel):
    """客户端公开配置"""

    max_upload_file_size: int
    max_chunk_size: int
    email_verification_enabled: bool = False
    email_verification_resend_interval_seconds: int = 60


@router.get("", response_model=PublicConfig)
async def get_public_config(db: Session = Depends(get_db)):
    """
    获取客户端公开配置

    返回文件上传限制等客户端需要的配置信息
    """
    upload_settings = RuntimeSettingsService.upload_settings(db)
    email_settings = EmailSettingsService.get_settings(db)
    return PublicConfig(
        max_upload_file_size=upload_settings.max_upload_file_size,
        max_chunk_size=upload_settings.max_chunk_size,
        email_verification_enabled=bool(email_settings.enabled),
        email_verification_resend_interval_seconds=int(
            email_settings.resend_interval_seconds or 60
        ),
    )
