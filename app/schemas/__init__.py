"""
Schemas层 - Pydantic模型定义（Views层）
"""

from .common import (
    ErrorResponse,
    HealthResponse,
    MessageResponse,
    PaginationParams,
)
from .user import (
    LoginResponse,
    SessionResponse,
    UserCreateRequest,
    UserListResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)

__all__ = [
    # 用户相关
    "UserRegisterRequest",
    "UserLoginRequest",
    "UserResponse",
    "UserUpdateRequest",
    "LoginResponse",
    "SessionResponse",
    "UserListResponse",
    "UserCreateRequest",
    # 通用
    "MessageResponse",
    "ErrorResponse",
    "PaginationParams",
    "HealthResponse",
]
