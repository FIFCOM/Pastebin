"""
Schemas层 - Pydantic模型定义（Views层）
"""

from .collab_room import (
    MemberInfo,
    MemberTokenPayload,
    MemberTokenResponse,
    OnlineMemberInfo,
    PasteShareRequest,
    RoomCreateRequest,
    RoomCreateResponse,
    RoomInfoResponse,
    RoomJoinRequest,
    RoomJoinResponse,
    RoomMembersResponse,
    RoomPastesResponse,
    SharedPasteInfo,
    WSAuthMessage,
    WSChatMessage,
    WSMemberJoinedMessage,
    WSMemberLeftMessage,
    WSPasteSharedMessage,
)
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
    # 协作房间相关
    "MemberTokenResponse",
    "MemberInfo",
    "RoomCreateRequest",
    "RoomCreateResponse",
    "RoomInfoResponse",
    "RoomJoinRequest",
    "RoomJoinResponse",
    "RoomMembersResponse",
    "OnlineMemberInfo",
    "PasteShareRequest",
    "SharedPasteInfo",
    "RoomPastesResponse",
    "MemberTokenPayload",
    # WebSocket消息
    "WSAuthMessage",
    "WSChatMessage",
    "WSPasteSharedMessage",
    "WSMemberJoinedMessage",
    "WSMemberLeftMessage",
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
