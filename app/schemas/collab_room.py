"""
协作房间相关的Pydantic模型
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ===============================
# 请求模型
# ===============================


class RoomCreateRequest(BaseModel):
    """创建协作房间请求（当前无需自定义参数）"""


class RoomJoinRequest(BaseModel):
    """加入房间请求"""

    pin_code: str = Field(..., min_length=6, max_length=6, description="6位PIN码")

    @field_validator("pin_code")
    @classmethod
    def validate_pin_code(cls, v):
        """验证PIN码格式"""
        replacement_map = {
            "O": "0",
            "I": "1",
            "L": "1",
        }
        allowed = set("ABCDEFGHJKMNPQRSTUVWXYZ0123456789")
        normalized = "".join(
            replacement_map.get(ch, ch)
            for ch in v.strip().upper()
            if replacement_map.get(ch, ch) in allowed
        )
        if len(normalized) != 6:
            raise ValueError("PIN码必须是6位不易混淆的字母数字组合")
        return normalized


class PasteShareRequest(BaseModel):
    """分享Paste到房间请求"""

    paste_id: str = Field(..., max_length=32, description="Paste ID")
    encrypted_paste_key: str = Field(
        ..., max_length=4096, description="用room_key加密的paste密钥（Base64）"
    )
    encrypted_admin_key: str | None = Field(
        None,
        max_length=4096,
        description="可选：用room_key加密的admin_key（Base64），提供后接收者可进入编辑",
    )
    target_member_id: str | None = Field(
        None, description="目标接收者ID，不提供则发送给所有人"
    )


# ===============================
# 响应模型
# ===============================


class MemberTokenResponse(BaseModel):
    """成员令牌响应"""

    member_token: str = Field(..., description="成员JWT令牌")
    display_name: str = Field(..., description="显示名称")


class MemberInfo(BaseModel):
    """成员信息"""

    id: str = Field(..., description="成员ID")
    display_name: str = Field(..., description="显示名称")
    joined_at: datetime = Field(..., description="加入时间")

    class Config:
        from_attributes = True


class RoomCreateResponse(BaseModel):
    """创建房间响应"""

    room_id: str = Field(..., description="房间ID")
    pin_code: str = Field(..., description="6位PIN码")
    join_url: str = Field(..., description="加入链接")
    max_members: int = Field(..., description="最大成员数")


class RoomInfoResponse(BaseModel):
    """房间信息响应（通过PIN码获取）"""

    room_id: str = Field(..., description="房间ID")
    member_count: int = Field(..., description="当前成员数")
    max_members: int = Field(..., description="最大成员数")

    class Config:
        from_attributes = True


class RoomJoinResponse(BaseModel):
    """加入房间响应"""

    room_key: str = Field(..., description="房间加密密钥（Base64）")
    members: list[MemberInfo] = Field(..., description="成员列表")
    ws_url: str = Field(..., description="WebSocket连接URL")


class OnlineMemberInfo(BaseModel):
    """在线成员信息"""

    member_id: str = Field(..., description="成员ID")
    display_name: str = Field(..., description="显示名称")
    last_seen: datetime = Field(..., description="最后活跃时间")
    is_online: bool = Field(..., description="是否在线（2分钟内活跃）")
    joined_at: datetime = Field(..., description="加入房间时间")

    class Config:
        from_attributes = True


class RoomMembersResponse(BaseModel):
    """房间成员列表响应"""

    members: list[OnlineMemberInfo] = Field(..., description="成员列表")


class SharedPasteInfo(BaseModel):
    """分享的Paste信息"""

    paste_id: str = Field(..., description="Paste ID")
    title: str | None = Field(default=None, description="Paste标题")
    encrypted_paste_key: str = Field(..., description="加密的Paste密钥")
    encrypted_admin_key: str | None = Field(
        default=None, description="加密的管理密钥，存在时表示可编辑"
    )
    shared_by: str = Field(..., description="分享者成员ID")
    target_member: str | None = Field(
        None, description="目标接收者成员ID，null表示群发"
    )
    shared_at: datetime = Field(..., description="分享时间")
    expire_at: datetime | None = Field(default=None, description="Paste过期时间")
    is_expired: bool = Field(default=False, description="Paste当前是否已过期")

    class Config:
        from_attributes = True


class RoomPastesResponse(BaseModel):
    """房间Paste列表响应"""

    pastes: list[SharedPasteInfo] = Field(..., description="Paste列表")


# ===============================
# WebSocket消息模型
# ===============================


class WSAuthMessage(BaseModel):
    """WebSocket认证消息"""

    type: Literal["auth"] = Field("auth", description="消息类型")
    token: str = Field(..., description="成员令牌")


class WSAuthOkMessage(BaseModel):
    type: str = Field("auth_ok", description="消息类型")
    room_id: str = Field(..., description="房间ID")
    member_id: str = Field(..., description="成员ID")
    display_name: str = Field(..., description="显示名称")
    timestamp: datetime = Field(..., description="认证成功时间戳")


class WSChatMessage(BaseModel):
    """WebSocket聊天消息"""

    type: str = Field("message", description="消息类型")
    encrypted_data: str = Field(..., description="加密的消息数据（Base64）")
    sender_id: str = Field(..., description="发送者成员ID")
    timestamp: datetime = Field(..., description="消息时间戳")


class WSPasteSharedMessage(BaseModel):
    """WebSocket Paste分享消息"""

    type: str = Field("paste_shared", description="消息类型")
    paste_id: str = Field(..., description="Paste ID")
    shared_by: str = Field(..., description="分享者成员ID")
    target_member: str | None = Field(
        None, description="目标接收者成员ID，null表示群发"
    )
    timestamp: datetime = Field(..., description="分享时间戳")


class WSMemberJoinedMessage(BaseModel):
    """WebSocket成员加入消息"""

    type: str = Field("member_joined", description="消息类型")
    member_id: str = Field(..., description="成员ID")
    display_name: str = Field(..., description="显示名称")
    timestamp: datetime = Field(..., description="加入时间戳")


class WSMemberLeftMessage(BaseModel):
    """WebSocket成员离开消息"""

    type: str = Field("member_left", description="消息类型")
    member_id: str = Field(..., description="成员ID")
    display_name: str = Field(..., description="显示名称")
    timestamp: datetime = Field(..., description="离开时间戳")


class WSErrorMessage(BaseModel):
    type: str = Field("error", description="消息类型")
    message: str = Field(..., description="错误信息")


class WSPingMessage(BaseModel):
    type: str = Field("ping", description="消息类型")


class WSPongMessage(BaseModel):
    type: str = Field("pong", description="消息类型")
    timestamp: datetime = Field(..., description="服务器响应时间")


# ===============================
# 内部使用的模型
# ===============================


class MemberTokenPayload(BaseModel):
    """成员令牌载荷（用于JWT）"""

    member_id: str = Field(..., description="成员ID")
    display_name: str = Field(..., description="显示名称")
    user_id: int | None = Field(default=None, description="关联的用户ID（可选）")
    exp: int = Field(..., description="过期时间戳")


class PinCodeGenerationResult(BaseModel):
    """PIN码生成结果"""

    pin_code: str = Field(..., description="生成的6位PIN码")
    attempts: int = Field(..., description="生成尝试次数")


# ===============================
# 工具函数
# ===============================


def calculate_is_online(last_seen: datetime) -> bool:
    """计算成员是否在线（2分钟内活跃）"""
    from datetime import timedelta

    from app.core.time_utils import coerce_utc, utc_now

    now = utc_now()
    return (now - coerce_utc(last_seen)) <= timedelta(minutes=2)


def build_join_url(pin_code: str, base_url: str = "") -> str:
    """构建房间加入链接"""
    if base_url:
        return f"{base_url.rstrip('/')}/join/{pin_code}"
    # 默认返回相对路径，避免写死域名误导前端
    return f"/join/{pin_code}"


def build_ws_url(room_id: str, base_url: str = "") -> str:
    """构建WebSocket连接URL"""
    if base_url:
        return f"{base_url.rstrip('/')}/api/rooms/{room_id}/ws"
    # 默认返回相对路径，由前端自行拼接 ws(s)://{host}
    return f"/api/rooms/{room_id}/ws"
