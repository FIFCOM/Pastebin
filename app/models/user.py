"""
用户数据模型
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan"
    )

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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"
