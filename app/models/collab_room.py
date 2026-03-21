"""
协作房间数据模型
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from config.config import settings


class Member(Base):
    """成员表，包含用户和游客"""

    __tablename__ = "members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )  # 可为空（游客）
    display_name = Column(String(50), nullable=False)  # Guest_xxxxx 或 username
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    expire_at = Column(DateTime, nullable=False)  # 24小时后过期

    # 关系
    user = relationship("User", foreign_keys=[user_id])
    created_rooms = relationship(
        "CollabRoom", back_populates="creator_member", cascade="all, delete-orphan"
    )
    room_memberships = relationship(
        "RoomMember", back_populates="member", cascade="all, delete-orphan"
    )
    shared_pastes = relationship(
        "RoomPaste",
        foreign_keys="RoomPaste.shared_by_member_id",
        back_populates="shared_by_member",
        cascade="all, delete-orphan",
    )
    received_pastes = relationship(
        "RoomPaste",
        foreign_keys="RoomPaste.target_member_id",
        back_populates="target_member",
    )

    # 索引定义
    __table_args__ = (
        Index("idx_member_user_id", "user_id"),  # 用户ID索引
        Index("idx_member_expire_at", "expire_at"),  # 过期时间索引，用于清理任务
        Index("idx_member_created_at", "created_at"),  # 创建时间索引
    )

    def __repr__(self):
        return f"<Member(id={self.id}, display_name={self.display_name}, user_id={self.user_id})>"


class CollabRoom(Base):
    """协作房间表"""

    __tablename__ = "collab_rooms"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    creator_member_id = Column(
        String(36),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )  # 级联删除
    pin_code = Column(String(6), unique=True, nullable=False, index=True)  # 6位字母数字
    room_key = Column(Text, nullable=False)  # 房间密钥，用于加密消息

    max_members = Column(
        Integer, default=settings.collab_room_max_members, nullable=False
    )  # 当前默认固定值由配置控制
    member_count = Column(Integer, default=1, nullable=False)  # 当前成员数
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # 关系
    creator_member = relationship("Member", back_populates="created_rooms")
    room_members = relationship(
        "RoomMember", back_populates="room", cascade="all, delete-orphan"
    )
    room_pastes = relationship(
        "RoomPaste", back_populates="room", cascade="all, delete-orphan"
    )

    # 索引定义
    __table_args__ = (
        Index("idx_collab_room_pin_code", "pin_code"),  # PIN码索引，用于快速查找
        Index("idx_collab_room_creator", "creator_member_id"),  # 创建者索引
        Index("idx_collab_room_created_at", "created_at"),  # 创建时间索引
    )

    def __repr__(self):
        return f"<CollabRoom(id={self.id}, pin_code={self.pin_code})>"


class RoomMember(Base):
    """房间成员关联表（简化版）"""

    __tablename__ = "room_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(
        String(36),
        ForeignKey("collab_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id = Column(
        String(36),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )  # 引用Member表

    last_seen = Column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )  # 最后活跃时间
    joined_at = Column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )  # 加入房间时间

    # 关系
    room = relationship("CollabRoom", back_populates="room_members")
    member = relationship("Member", back_populates="room_memberships")

    # 索引和约束定义
    __table_args__ = (
        UniqueConstraint(
            "room_id", "member_id", name="uq_room_member"
        ),  # 确保成员不能重复加入同一房间
        Index("idx_room_member", "room_id", "member_id"),  # 复合索引
        Index("idx_room_member_last_seen", "last_seen"),  # 最后活跃时间索引
    )

    def __repr__(self):
        return f"<RoomMember(id={self.id}, room_id={self.room_id}, member_id={self.member_id})>"


class RoomPaste(Base):
    """房间分享的Paste"""

    __tablename__ = "room_pastes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(
        String(36),
        ForeignKey("collab_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paste_id = Column(
        String(32),
        ForeignKey("pastes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shared_by_member_id = Column(
        String(36),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )  # 分享者
    target_member_id = Column(
        String(36),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # 目标接收者，null表示发送给所有人

    encrypted_paste_key = Column(Text, nullable=False)  # 用room_key加密的paste密钥
    encrypted_admin_key = Column(Text, nullable=True)  # 用room_key加密的admin_key

    shared_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # 关系
    room = relationship("CollabRoom", back_populates="room_pastes")
    paste = relationship("Paste")
    shared_by_member = relationship(
        "Member", foreign_keys=[shared_by_member_id], back_populates="shared_pastes"
    )
    target_member = relationship(
        "Member", foreign_keys=[target_member_id], back_populates="received_pastes"
    )

    # 索引定义
    __table_args__ = (
        Index(
            "idx_room_paste_target", "room_id", "target_member_id"
        ),  # 房间+目标成员复合索引
        Index("idx_room_paste_shared_by", "shared_by_member_id"),  # 分享者索引
        Index("idx_room_paste_shared_at", "shared_at"),  # 分享时间索引
        Index("idx_room_paste_paste_id", "paste_id"),  # paste_id索引
    )

    def __repr__(self):
        return f"<RoomPaste(id={self.id}, room_id={self.room_id}, paste_id={self.paste_id})>"
