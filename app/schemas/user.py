"""
用户相关的Pydantic模型
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, validator


class UserRegisterRequest(BaseModel):
    """用户注册请求"""

    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA256哈希后的密码(64位十六进制字符串)",
    )

    @validator("password")
    def validate_password_hash(cls, v):
        """验证密码是否为有效的SHA256哈希"""
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("密码必须是有效的SHA256哈希(64位十六进制字符串)")
        return v.lower()  # 统一转为小写


class UserLoginRequest(BaseModel):
    """用户登录请求"""

    username: str = Field(..., description="用户名")
    password: str = Field(
        ..., min_length=64, max_length=64, description="SHA256哈希后的密码"
    )

    @validator("password")
    def validate_password_hash(cls, v):
        """验证密码是否为有效的SHA256哈希"""
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("密码必须是有效的SHA256哈希(64位十六进制字符串)")
        return v.lower()


class UserResponse(BaseModel):
    """用户响应"""

    id: int
    username: str
    email: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """用户更新请求"""

    email: EmailStr | None = Field(None, description="用户邮箱")
    password: str | None = Field(
        None, min_length=64, max_length=64, description="SHA256哈希后的新密码"
    )

    @validator("password")
    def validate_password_hash(cls, v):
        """验证密码是否为有效的SHA256哈希"""
        if v is not None:
            if not all(c in "0123456789abcdefABCDEF" for c in v):
                raise ValueError("密码必须是有效的SHA256哈希(64位十六进制字符串)")
            return v.lower()
        return v


class LoginResponse(BaseModel):
    """登录响应"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SessionResponse(BaseModel):
    """会话响应"""

    id: str
    user_id: int
    expires_at: datetime
    created_at: datetime

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

    username: str | None = Field(None, description="用户名，留空则自动生成")
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(
        ..., min_length=64, max_length=64, description="SHA256哈希后的密码"
    )

    @validator("password")
    def validate_password_hash(cls, v):
        """验证密码是否为有效的SHA256哈希"""
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("密码必须是有效的SHA256哈希(64位十六进制字符串)")
        return v.lower()
