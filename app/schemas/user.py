"""
用户相关的Pydantic模型
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.validators import normalize_sha256_hex


class UserRegisterRequest(BaseModel):
    """用户注册请求"""

    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA256哈希后的密码(64位十六进制字符串)",
    )

    @field_validator("password")
    @classmethod
    def validate_password_hash(cls, v):
        """验证密码是否为有效的SHA256哈希"""
        normalized = normalize_sha256_hex(v)
        return str(normalized)  # 统一转为小写


class UserLoginRequest(BaseModel):
    """用户登录请求"""

    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(
        ..., min_length=64, max_length=64, description="SHA256哈希后的密码"
    )

    @field_validator("password")
    @classmethod
    def validate_password_hash(cls, v):
        """验证密码是否为有效的SHA256哈希"""
        normalized = normalize_sha256_hex(v)
        return str(normalized)


class UserLoginWithTotpRequest(BaseModel):
    """用户TOTP登录请求"""

    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(
        ..., min_length=64, max_length=64, description="SHA256哈希后的密码"
    )
    totp_code: str = Field(..., min_length=6, max_length=6, description="6位TOTP验证码")

    @field_validator("password")
    @classmethod
    def validate_password_hash(cls, v):
        """验证密码是否为有效的SHA256哈希"""
        normalized = normalize_sha256_hex(v)
        return str(normalized)

    @field_validator("totp_code")
    @classmethod
    def validate_totp_code(cls, v):
        """验证TOTP代码格式"""
        if not v.isdigit():
            raise ValueError("TOTP代码必须是6位数字")
        return v


class UserResponse(BaseModel):
    """用户响应"""

    id: int
    username: str
    email: str | None
    role: Literal["admin", "user"] = "user"
    is_active: bool = True
    totp_enabled: bool = False  # 是否启用TOTP
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """用户更新请求"""

    username: str | None = Field(default=None, description="用户名")
    email: EmailStr | None = Field(default=None, description="用户邮箱")
    current_password: str | None = Field(
        None, min_length=64, max_length=64, description="当前密码（SHA256哈希）"
    )
    password: str | None = Field(
        None, min_length=64, max_length=64, description="SHA256哈希后的新密码"
    )
    role: Literal["admin", "user"] | None = Field(default=None, description="用户角色")
    is_active: bool | None = Field(default=None, description="用户是否可登录")

    @field_validator("current_password", "password")
    @classmethod
    def validate_password_hash(cls, v):
        """验证密码是否为有效的SHA256哈希"""
        return normalize_sha256_hex(v)


class LoginResponse(BaseModel):
    """登录响应"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenResponse(BaseModel):
    """refresh token 续期响应"""

    access_token: str
    token_type: str = "bearer"


class SessionResponse(BaseModel):
    """会话响应"""

    id: str
    user_id: int
    expires_at: datetime
    created_at: datetime
    user_agent: str | None = None
    ip_address: str | None = None
    last_active_at: datetime | None = None
    is_current: bool = False

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表响应"""

    users: list[UserResponse]
    total: int
    page: int
    size: int


class UserCreateRequest(BaseModel):
    """管理员创建用户请求"""

    username: str | None = Field(default=None, description="用户名，留空则自动生成")
    email: EmailStr = Field(..., description="用户邮箱")
    role: Literal["admin", "user"] = Field(default="user", description="用户角色")
    password: str = Field(
        ..., min_length=64, max_length=64, description="SHA256哈希后的密码"
    )

    @field_validator("password")
    @classmethod
    def validate_password_hash(cls, v):
        """验证密码是否为有效的SHA256哈希"""
        normalized = normalize_sha256_hex(v)
        return str(normalized)


class TotpSetupResponse(BaseModel):
    """TOTP设置响应"""

    secret: str = Field(..., description="TOTP密钥")
    provisioning_uri: str = Field(..., description="用于生成二维码的 otpauth URI")


class TotpVerifyRequest(BaseModel):
    """TOTP验证请求"""

    totp_code: str = Field(..., min_length=6, max_length=6, description="6位TOTP验证码")

    @field_validator("totp_code")
    @classmethod
    def validate_totp_code(cls, v):
        """验证TOTP代码格式"""
        if not v.isdigit():
            raise ValueError("TOTP代码必须是6位数字")
        return v


class TotpStatusResponse(BaseModel):
    """TOTP状态响应"""

    enabled: bool = Field(..., description="是否已启用TOTP")
    setup_required: bool = Field(default=False, description="是否需要设置TOTP")
