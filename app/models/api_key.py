"""
API Key数据模型
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class ApiKey(Base):
    """API密钥表模型"""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(100), nullable=False)  # API密钥名称
    key_hash = Column(
        String(255), unique=True, nullable=False, index=True
    )  # API key的哈希值
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # 关系
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<ApiKey(id={self.id}, user_id={self.user_id}, name={self.name})>"
