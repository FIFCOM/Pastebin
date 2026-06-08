"""
邮箱验证配置相关 Pydantic 模型
"""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

SmtpSecurity = Literal["none", "starttls", "ssl"]


class EmailVerificationSettingsResponse(BaseModel):
    """邮箱验证配置响应。"""

    enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_security: SmtpSecurity = "starttls"
    smtp_username: str | None = None
    smtp_password_configured: bool = False
    smtp_from_email: str | None = None
    smtp_from_name: str = "Material Bin"
    code_ttl_minutes: int = 10
    resend_interval_seconds: int = 60
    max_attempts: int = 5


class EmailVerificationSettingsUpdateRequest(BaseModel):
    """邮箱验证配置更新请求。"""

    enabled: bool = False
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_security: SmtpSecurity = "starttls"
    smtp_username: str | None = Field(default=None, max_length=255)
    smtp_password: str | None = Field(default=None, max_length=1024)
    clear_smtp_password: bool = False
    smtp_from_email: EmailStr | None = None
    smtp_from_name: str = Field(default="Material Bin", min_length=1, max_length=255)
    code_ttl_minutes: int = Field(default=10, ge=1, le=120)
    resend_interval_seconds: int = Field(default=60, ge=10, le=3600)
    max_attempts: int = Field(default=5, ge=1, le=20)

    @field_validator("smtp_host", "smtp_username", mode="before")
    @classmethod
    def normalize_optional_string(cls, value):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("smtp_password", mode="before")
    @classmethod
    def normalize_optional_password(cls, value):
        if value is None:
            return None
        return str(value) or None

    @field_validator("smtp_from_name")
    @classmethod
    def normalize_from_name(cls, value: str):
        normalized = value.strip()
        if not normalized:
            raise ValueError("发件人名称不能为空")
        return normalized
