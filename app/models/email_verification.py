"""
邮箱验证相关数据模型
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
)

from app.core.database import Base


class EmailVerificationSetting(Base):
    """邮箱验证码与 SMTP 配置。"""

    __tablename__ = "email_verification_settings"

    id = Column(Integer, primary_key=True, default=1)
    enabled = Column(Boolean, nullable=False, default=False, index=True)
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=False, default=587)
    smtp_security = Column(String(20), nullable=False, default="starttls")
    smtp_username = Column(String(255), nullable=True)
    smtp_password_encrypted = Column(Text, nullable=True)
    smtp_from_email = Column(String(255), nullable=True)
    smtp_from_name = Column(String(255), nullable=False, default="Material Bin")
    code_ttl_minutes = Column(Integer, nullable=False, default=10)
    resend_interval_seconds = Column(Integer, nullable=False, default=60)
    max_attempts = Column(Integer, nullable=False, default=5)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    def __repr__(self):
        return "<EmailVerificationSetting(id=1)>"


class EmailVerificationCode(Base):
    """邮箱验证码记录。"""

    __tablename__ = "email_verification_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    purpose = Column(String(32), nullable=False, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    code_hash = Column(String(64), nullable=False)
    nonce = Column(String(64), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    ip_address = Column(String(64), nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    consumed_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        Index(
            "idx_email_verification_lookup",
            "email",
            "purpose",
            "user_id",
            "consumed_at",
            "created_at",
        ),
    )

    def __repr__(self):
        return f"<EmailVerificationCode(id={self.id}, email={self.email}, purpose={self.purpose})>"
