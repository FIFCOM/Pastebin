"""
Paste数据模型
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Paste(Base):
    """Paste主表（包含草稿状态）"""

    __tablename__ = "pastes"

    id = Column(String(32), primary_key=True)  # 短ID，如 "x7h9k2m4"

    # 状态管理
    status = Column(Enum("draft", "published", "edited"), default="draft")

    # METADATA
    title = Column(String(255))
    type = Column(Enum("txt", "md"), default="txt")  # paste类型，默认为txt，可选md
    content_path = Column(String(500))  # 加密内容文件路径

    # 加密相关
    encryption_mode = Column(Enum("client", "server"), default="client")
    admin_key = Column(
        String(32)
    )  # 管理权限令牌，由服务器生成，仅用于权限验证，不作为加解密密钥
    access_key_hash = Column(
        String(255), nullable=True
    )  # bcrypt加密的访问密钥，仅用于权限验证，不作为加解密密钥

    max_views = Column(Integer)  # 为1时表示阅后即焚，为-1时表示无限制

    # 统计
    view_count = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime)  # 发布时间
    expire_at = Column(DateTime)  # 既可以表示draft的过期时间，也可以表示paste的过期时间

    # 关系
    files = relationship("File", back_populates="paste", cascade="all, delete-orphan")
    paste_keys = relationship(
        "PasteKey", back_populates="paste", cascade="all, delete-orphan"
    )

    # 索引定义
    __table_args__ = (
        Index("idx_paste_status", "status"),  # 状态索引，用于频繁查询
        Index("idx_paste_expire_at", "expire_at"),  # 过期时间索引，用于清理任务
        Index("idx_paste_created_at", "created_at"),  # 创建时间索引，用于排序
        Index(
            "idx_paste_status_expire", "status", "expire_at"
        ),  # 复合索引，用于状态+过期时间的复合查询
    )

    def __repr__(self):
        return f"<Paste(id={self.id}, status={self.status}, title={self.title})>"


class PasteKey(Base):
    """Paste的服务端加密密钥表
    TODO: 建议迁移到Redis存储，提高安全性
    """

    __tablename__ = "paste_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paste_id = Column(
        String(32), ForeignKey("pastes.id", ondelete="CASCADE")
    )  # 级联删除

    # 临时保存的、用于加密的paste密钥
    # TODO: 考虑迁移到Redis
    paste_key = Column(Text, nullable=False)

    # 关系
    paste = relationship("Paste", back_populates="paste_keys")

    # 索引定义
    __table_args__ = (
        Index("idx_paste_key_paste_id", "paste_id"),  # paste_id索引，用于快速查找
    )

    def __repr__(self):
        return f"<PasteKey(id={self.id}, paste_id={self.paste_id})>"


class File(Base):
    """文件表"""

    __tablename__ = "files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    paste_id = Column(String(32), ForeignKey("pastes.id", ondelete="CASCADE"))

    # 文件信息
    file_name_encrypted = Column(Text)  # 加密的文件名
    mime_type = Column(Text)  # MIME类型
    file_size = Column(BigInteger, nullable=False)
    storage_path = Column(Text, nullable=False)  # 存储路径
    checksum = Column(String(64))

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    paste = relationship("Paste", back_populates="files")

    def __repr__(self):
        return f"<File(id={self.id}, paste_id={self.paste_id}, size={self.file_size})>"
