"""
用户Paste关联数据模型
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserPaste(Base):
    """用户Paste关联表"""

    __tablename__ = "user_pastes"

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

    # 加密的paste密钥
    encrypted_paste_key = Column(Text, nullable=False)

    # 用户是否标记为收藏
    is_starred = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User")
    paste = relationship("Paste")

    # 索引和约束定义
    __table_args__ = (UniqueConstraint("user_id", "paste_id", name="uq_user_paste"),)

    def __repr__(self):
        return f"<UserPaste(id={self.id}, user_id={self.user_id}, paste_id={self.paste_id}, is_starred={self.is_starred})>"
