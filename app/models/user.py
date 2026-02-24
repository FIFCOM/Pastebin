"""
用户数据模型
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """用户表模型"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(
        String(255), unique=True, nullable=False, index=True
    )  # 自动生成: USER_RANDOMSTR
    email = Column(
        String(255), unique=True, nullable=True, index=True
    )  # 用户注册时提供
    password_hash = Column(String(255), nullable=False)  # bcrypt加密的密码
    salt = Column(String(255), nullable=False)  # 用于派生 master_key
    encrypted_user_key = Column(Text, nullable=False)  # 加密的用户密钥
    totp_secret = Column(String(255), nullable=True)  # 加密的TOTP密钥，空值表示未启用
    # TOTP 设置流程：setup 阶段写入 pending，verify 成功后提升为 totp_secret
    totp_pending_secret = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, default="user", index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # 关系
    sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def totp_enabled(self) -> bool:
        """Pydantic UserResponse.totp_enabled 的来源字段。"""
        return bool(self.totp_secret)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class UserSession(Base):
    """用户会话表模型"""

    __tablename__ = "user_sessions"

    # 对于SQLite，使用TEXT类型存储UUID字符串；对于PostgreSQL使用UUID类型
    id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    encrypted_session_key = Column(Text, nullable=False)  # 会话加密的用户密钥
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    last_active_at = Column(DateTime, nullable=True)

    # 关系
    user = relationship("User", back_populates="sessions")
    session_key = relationship(
        "UserSessionKey",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )
    used_refresh_tokens = relationship(
        "UsedRefreshToken", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"


class UserSessionKey(Base):
    """用户会话密钥表模型（用于服务端恢复 user_key）"""

    __tablename__ = "user_session_keys"

    session_id = Column(
        String(36),
        ForeignKey("user_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    encrypted_session_key = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    session = relationship("UserSession", back_populates="session_key")

    def __repr__(self):
        return f"<UserSessionKey(session_id={self.session_id})>"


class UsedRefreshToken(Base):
    """已使用（被旋转替换）的 refresh token 哈希，用于检测复用"""

    __tablename__ = "used_refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36),
        ForeignKey("user_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    replaced_by_hash = Column(String(64), nullable=False)
    used_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    session = relationship("UserSession", back_populates="used_refresh_tokens")

    def __repr__(self):
        return f"<UsedRefreshToken(id={self.id}, session_id={self.session_id}, used_at={self.used_at})>"
