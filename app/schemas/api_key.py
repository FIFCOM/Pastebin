"""
API Key相关的Pydantic模型
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    """创建API密钥请求"""

    name: str = Field(..., min_length=1, max_length=100, description="API密钥名称")
    expires_in_days: int | None = Field(
        default=None,
        ge=1,
        le=3650,
        description="可选，到期天数（不填表示不过期）",
    )


class ApiKeyResponse(BaseModel):
    """API密钥响应"""

    id: int
    name: str
    key_preview: str | None = None
    created_at: datetime
    last_used_at: datetime | None = None
    last_used_ip: str | None = None
    expires_at: datetime | None = None

    class Config:
        from_attributes = True


class ApiKeyCreateResponse(BaseModel):
    """创建API密钥响应（包含密钥明文）"""

    id: int
    name: str
    api_key: str = Field(..., description="API密钥明文（仅创建时返回一次）")
    key_preview: str | None = None
    created_at: datetime
    last_used_at: datetime | None = None
    last_used_ip: str | None = None
    expires_at: datetime | None = None

    class Config:
        from_attributes = True


class ApiKeyListResponse(BaseModel):
    """API密钥列表响应"""

    api_keys: list[ApiKeyResponse]
