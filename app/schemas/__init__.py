"""
Schemas层 - Pydantic模型定义（Views层）
"""

from .cleanup import (
    CleanupRequest,
    CleanupResponse,
    CleanupTaskResult,
    InternalAuthRequest,
)
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
    WSAuthOkMessage,
    WSChatMessage,
    WSErrorMessage,
    WSMemberJoinedMessage,
    WSMemberLeftMessage,
    WSPasteSharedMessage,
    WSPingMessage,
    WSPongMessage,
)
from .common import (
    ErrorResponse,
    HealthResponse,
    MessageResponse,
    PaginationParams,
)
from .runtime_settings import (
    RuntimeSettingItem,
    RuntimeSettingsResponse,
    RuntimeSettingsUpdateRequest,
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
    # 清理任务相关
    "CleanupRequest",
    "CleanupResponse",
    "CleanupTaskResult",
    "InternalAuthRequest",
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
    "WSAuthOkMessage",
    "WSChatMessage",
    "WSErrorMessage",
    "WSPasteSharedMessage",
    "WSMemberJoinedMessage",
    "WSMemberLeftMessage",
    "WSPingMessage",
    "WSPongMessage",
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
    "RuntimeSettingItem",
    "RuntimeSettingsResponse",
    "RuntimeSettingsUpdateRequest",
]
