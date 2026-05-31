"""
用户收藏Paste关联数据模型
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


class UserFavorite(Base):
    """用户收藏Paste关联表"""

    __tablename__ = "user_favorites"

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

    # 加密的paste解密密钥（使用用户密钥加密）
    encrypted_paste_key = Column(Text, nullable=False)

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

    __table_args__ = (
        UniqueConstraint("user_id", "paste_id", name="uq_user_favorite"),
        Index("idx_user_favorite_list", "user_id", "is_deleted", "updated_at"),
    )

    def __repr__(self):
        return f"<UserFavorite(id={self.id}, user_id={self.user_id}, paste_id={self.paste_id}, is_deleted={self.is_deleted})>"
