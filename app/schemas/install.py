"""
安装向导相关模型
"""

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.validators import normalize_sha256_hex


class InstallEnvItem(BaseModel):
    key: str
    default_value: str = ""
    comment: str | None = None
    required: bool = False
    advanced: bool = False
    group: str | None = None


class InstallContextResponse(BaseModel):
    needs_install: bool
    env_exists: bool
    admin_exists: bool
    env_template: list[InstallEnvItem]
    restart_required: bool = False
    restart_message: str | None = None


class InstallErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int
    code: str


class InstallSetupRequest(BaseModel):
    env_values: dict[str, str] = Field(default_factory=dict)
    admin_email: EmailStr | None = Field(default=None, description="管理员邮箱")
    admin_password: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        description="管理员密码（SHA256哈希）",
    )

    @field_validator("admin_password")
    @classmethod
    def validate_password_hash(cls, v: str | None) -> str | None:
        return normalize_sha256_hex(v)


class InstallSetupResponse(BaseModel):
    message: str
    env_created: bool
    admin_created: bool
    restart_required: bool = False
