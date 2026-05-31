"""
用户History关联数据模型
"""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
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


class UserHistory(Base):
    """用户History关联表"""

    __tablename__ = "user_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    paste_id = Column(
        String(32),
        ForeignKey("pastes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 加密的paste密钥（使用用户密钥加密）
    encrypted_paste_key = Column(Text, nullable=False)

    # 加密的admin_key（使用用户密钥加密，不明文存储）
    encrypted_admin_key = Column(Text, nullable=False)

    # 软删除标记
    is_deleted = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # 关系
    user = relationship("User")
    paste = relationship("Paste")

    # 索引和约束定义
    __table_args__ = (
        UniqueConstraint("user_id", "paste_id", name="uq_user_history"),
        Index("idx_user_history_list", "user_id", "is_deleted", "updated_at"),
    )

    def __repr__(self):
        return f"<UserHistory(id={self.id}, user_id={self.user_id}, paste_id={self.paste_id}, is_deleted={self.is_deleted})>"
