"""
邮箱验证码服务
"""

import hmac
import logging
import secrets
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Literal, cast

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.email_verification import (
    EmailVerificationCode,
    EmailVerificationSetting,
)
from app.models.user import User
from app.services.email_settings_service import EmailSettingsService
from config.config import settings

EmailVerificationPurpose = Literal["register", "reset_password", "change_email"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailVerificationDispatch:
    """待后台发送的邮箱验证码。"""

    record_id: int
    code: str


class EmailVerificationService:
    """邮箱验证码发送与校验。"""

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _code_hash(
        email: str, purpose: EmailVerificationPurpose, nonce: str, code: str
    ) -> str:
        message = f"{EmailVerificationService.normalize_email(email)}:{purpose}:{nonce}:{code}"
        return hmac.new(
            settings.secret_key.encode("utf-8"),
            message.encode("utf-8"),
            "sha256",
        ).hexdigest()

    @staticmethod
    def _find_user_by_email(db: Session, email: str) -> User | None:
        normalized = EmailVerificationService.normalize_email(email)
        return db.query(User).filter(func.lower(User.email) == normalized).first()

    @staticmethod
    def _assert_enabled(row: EmailVerificationSetting) -> None:
        if not row.enabled:
            raise ValueError("邮箱验证码功能未启用")

    @staticmethod
    def _assert_smtp_ready(row: EmailVerificationSetting) -> None:
        if not row.smtp_host or not row.smtp_from_email:
            raise ValueError("SMTP配置不完整，请先在系统配置中填写SMTP服务器和发件邮箱")

    @staticmethod
    def _latest_unconsumed(
        db: Session,
        *,
        email: str,
        purpose: EmailVerificationPurpose,
        user_id: int | None,
    ) -> EmailVerificationCode | None:
        return (
            db.query(EmailVerificationCode)
            .filter(
                EmailVerificationCode.email
                == EmailVerificationService.normalize_email(email),
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.user_id == user_id,
                EmailVerificationCode.consumed_at.is_(None),
            )
            .order_by(EmailVerificationCode.created_at.desc())
            .first()
        )

    @staticmethod
    def _send_mail(
        row: EmailVerificationSetting,
        *,
        to_email: str,
        purpose: EmailVerificationPurpose,
        code: str,
    ) -> None:
        from_email = str(row.smtp_from_email or "").strip()
        from_name = str(row.smtp_from_name or "Material Bin").strip()
        subject_map = {
            "register": "Material Bin 注册验证码",
            "reset_password": "Material Bin 密码重置验证码",
            "change_email": "Material Bin 修改邮箱验证码",
        }
        action_map = {
            "register": "完成注册",
            "reset_password": "重置密码",
            "change_email": "修改邮箱",
        }

        message = EmailMessage()
        message["Subject"] = subject_map[purpose]
        message["From"] = f"{from_name} <{from_email}>"
        message["To"] = to_email
        message.set_content(
            "\n".join(
                [
                    f"你的验证码是：{code}",
                    "",
                    f"该验证码用于{action_map[purpose]}，请在有效期内使用。",
                    "如果不是你本人操作，可以忽略这封邮件。",
                ]
            )
        )

        host = str(row.smtp_host)
        port = int(row.smtp_port or 587)
        security = str(row.smtp_security or "starttls")
        username = str(row.smtp_username).strip() if row.smtp_username else None
        password = EmailSettingsService.decrypt_password(row)

        if security == "ssl":
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            smtp = smtplib.SMTP(host, port, timeout=15)

        try:
            smtp.ehlo()
            if security == "starttls":
                smtp.starttls()
                smtp.ehlo()
            if username:
                smtp.login(username, password or "")
            smtp.send_message(message)
        finally:
            smtp.quit()

    @staticmethod
    def _send_code(
        db: Session,
        *,
        row: EmailVerificationSetting,
        email: str,
        purpose: EmailVerificationPurpose,
        user_id: int | None,
        ip_address: str | None,
    ) -> None:
        normalized_email = EmailVerificationService.normalize_email(email)
        now = datetime.now(UTC)

        latest = EmailVerificationService._latest_unconsumed(
            db, email=normalized_email, purpose=purpose, user_id=user_id
        )
        if latest is not None:
            created_at = latest.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            elapsed = (now - created_at).total_seconds()
            if elapsed < int(row.resend_interval_seconds or 60):
                raise ValueError("验证码发送过于频繁，请稍后再试")

        (
            db.query(EmailVerificationCode)
            .filter(
                EmailVerificationCode.email == normalized_email,
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.user_id == user_id,
                EmailVerificationCode.consumed_at.is_(None),
            )
            .update({EmailVerificationCode.consumed_at: now})
        )

        code = f"{secrets.randbelow(1_000_000):06d}"
        nonce = secrets.token_urlsafe(24)
        record = EmailVerificationCode(
            email=normalized_email,
            purpose=purpose,
            user_id=user_id,
            code_hash=EmailVerificationService._code_hash(
                normalized_email, purpose, nonce, code
            ),
            nonce=nonce,
            attempts=0,
            ip_address=ip_address,
            expires_at=now + timedelta(minutes=int(row.code_ttl_minutes or 10)),
        )
        db.add(record)
        db.flush()

        try:
            EmailVerificationService._send_mail(
                row,
                to_email=normalized_email,
                purpose=purpose,
                code=code,
            )
        except Exception as e:
            db.rollback()
            raise ValueError(f"发送验证码失败: {str(e)}") from e

        db.commit()

    @staticmethod
    def _create_dispatchable_code(
        db: Session,
        *,
        row: EmailVerificationSetting,
        email: str,
        purpose: Literal["register", "reset_password"],
        ip_address: str | None,
    ) -> EmailVerificationDispatch:
        normalized_email = EmailVerificationService.normalize_email(email)
        now = datetime.now(UTC)

        latest = EmailVerificationService._latest_unconsumed(
            db, email=normalized_email, purpose=purpose, user_id=None
        )
        if latest is not None:
            created_at = latest.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            elapsed = (now - created_at).total_seconds()
            if elapsed < int(row.resend_interval_seconds or 60):
                raise ValueError("验证码发送过于频繁，请稍后再试")

        (
            db.query(EmailVerificationCode)
            .filter(
                EmailVerificationCode.email == normalized_email,
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.user_id.is_(None),
                EmailVerificationCode.consumed_at.is_(None),
            )
            .update({EmailVerificationCode.consumed_at: now})
        )

        code = f"{secrets.randbelow(1_000_000):06d}"
        nonce = secrets.token_urlsafe(24)
        record = EmailVerificationCode(
            email=normalized_email,
            purpose=purpose,
            user_id=None,
            code_hash=EmailVerificationService._code_hash(
                normalized_email, purpose, nonce, code
            ),
            nonce=nonce,
            attempts=0,
            ip_address=ip_address,
            expires_at=now + timedelta(minutes=int(row.code_ttl_minutes or 10)),
        )
        db.add(record)
        db.flush()

        record_id = getattr(record, "id", None)
        if not isinstance(record_id, int):
            db.rollback()
            raise ValueError("验证码记录创建失败")

        db.commit()
        return EmailVerificationDispatch(record_id=record_id, code=code)

    @staticmethod
    def send_prepared_code(record_id: int, code: str) -> None:
        """后台发送已创建的公开邮箱验证码。"""
        from app.core.database import SessionLocal

        with SessionLocal() as db:
            now = datetime.now(UTC)
            record = (
                db.query(EmailVerificationCode)
                .filter(EmailVerificationCode.id == record_id)
                .first()
            )
            if record is None or record.consumed_at is not None:
                return

            expires_at = record.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at < now:
                record.consumed_at = now  # type: ignore[assignment]
                db.commit()
                return

            purpose_text = str(record.purpose)
            if purpose_text not in ("register", "reset_password"):
                record.consumed_at = now  # type: ignore[assignment]
                db.commit()
                return

            try:
                row = EmailSettingsService.get_settings(db)
                EmailVerificationService._assert_enabled(row)
                EmailVerificationService._assert_smtp_ready(row)
                EmailVerificationService._send_mail(
                    row,
                    to_email=str(record.email),
                    purpose=cast(EmailVerificationPurpose, purpose_text),
                    code=code,
                )
            except Exception:
                logger.exception(
                    "公开邮箱验证码后台发送失败 record_id=%s purpose=%s",
                    record_id,
                    purpose_text,
                )
                try:
                    record.consumed_at = now  # type: ignore[assignment]
                    db.commit()
                except Exception:
                    db.rollback()
                    logger.exception(
                        "公开邮箱验证码后台发送失败后作废记录失败 record_id=%s",
                        record_id,
                    )

    @staticmethod
    def _reserve_public_send_interval(
        db: Session,
        *,
        row: EmailVerificationSetting,
        email: str,
        purpose: Literal["register", "reset_password"],
        ip_address: str | None,
    ) -> None:
        """
        记录一次公开验证码请求，但不发送邮件。

        用于邮箱不适用当前用途的场景，保持响应和重发间隔一致，
        避免通过重复请求枚举注册邮箱。
        """
        normalized_email = EmailVerificationService.normalize_email(email)
        now = datetime.now(UTC)

        latest = EmailVerificationService._latest_unconsumed(
            db, email=normalized_email, purpose=purpose, user_id=None
        )
        if latest is not None:
            created_at = latest.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            elapsed = (now - created_at).total_seconds()
            if elapsed < int(row.resend_interval_seconds or 60):
                raise ValueError("验证码发送过于频繁，请稍后再试")

        (
            db.query(EmailVerificationCode)
            .filter(
                EmailVerificationCode.email == normalized_email,
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.user_id.is_(None),
                EmailVerificationCode.consumed_at.is_(None),
            )
            .update({EmailVerificationCode.consumed_at: now})
        )

        nonce = secrets.token_urlsafe(24)
        phantom_code = secrets.token_urlsafe(18)
        record = EmailVerificationCode(
            email=normalized_email,
            purpose=purpose,
            user_id=None,
            code_hash=EmailVerificationService._code_hash(
                normalized_email, purpose, nonce, phantom_code
            ),
            nonce=nonce,
            attempts=0,
            ip_address=ip_address,
            expires_at=now,
        )
        db.add(record)
        db.commit()

    @staticmethod
    def send_public_code(
        db: Session,
        *,
        email: str,
        purpose: Literal["register", "reset_password"],
        ip_address: str | None = None,
    ) -> EmailVerificationDispatch | None:
        row = EmailSettingsService.get_settings(db)
        EmailVerificationService._assert_enabled(row)
        EmailVerificationService._assert_smtp_ready(row)

        user = EmailVerificationService._find_user_by_email(db, email)
        if purpose == "register" and user is not None:
            EmailVerificationService._reserve_public_send_interval(
                db,
                row=row,
                email=email,
                purpose=purpose,
                ip_address=ip_address,
            )
            return
        if purpose == "reset_password" and user is None:
            EmailVerificationService._reserve_public_send_interval(
                db,
                row=row,
                email=email,
                purpose=purpose,
                ip_address=ip_address,
            )
            return

        return EmailVerificationService._create_dispatchable_code(
            db,
            row=row,
            email=email,
            purpose=purpose,
            ip_address=ip_address,
        )

    @staticmethod
    def send_change_email_code(
        db: Session,
        *,
        email: str,
        user_id: int,
        ip_address: str | None = None,
    ) -> None:
        row = EmailSettingsService.get_settings(db)
        EmailVerificationService._assert_enabled(row)
        EmailVerificationService._assert_smtp_ready(row)

        existing = EmailVerificationService._find_user_by_email(db, email)
        if existing is not None and int(existing.id) != user_id:
            raise ValueError("邮箱已被其他用户使用")

        EmailVerificationService._send_code(
            db,
            row=row,
            email=email,
            purpose="change_email",
            user_id=user_id,
            ip_address=ip_address,
        )

    @staticmethod
    def consume_code(
        db: Session,
        *,
        email: str,
        purpose: EmailVerificationPurpose,
        code: str,
        user_id: int | None = None,
    ) -> None:
        row = EmailSettingsService.get_settings(db)
        EmailVerificationService._assert_enabled(row)

        normalized_email = EmailVerificationService.normalize_email(email)
        now = datetime.now(UTC)
        record = (
            db.query(EmailVerificationCode)
            .filter(
                EmailVerificationCode.email == normalized_email,
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.user_id == user_id,
                EmailVerificationCode.consumed_at.is_(None),
            )
            .order_by(EmailVerificationCode.created_at.desc())
            .first()
        )

        if record is None:
            raise ValueError("验证码无效或已过期")

        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < now:
            record.consumed_at = now  # type: ignore[assignment]
            db.commit()
            raise ValueError("验证码无效或已过期")

        if int(record.attempts or 0) >= int(row.max_attempts or 5):
            raise ValueError("验证码尝试次数已达上限")

        expected_hash = EmailVerificationService._code_hash(
            normalized_email, purpose, str(record.nonce), code
        )
        if not hmac.compare_digest(str(record.code_hash), expected_hash):
            record.attempts = int(record.attempts or 0) + 1  # type: ignore[assignment]
            db.commit()
            raise ValueError("验证码错误")

        record.consumed_at = now  # type: ignore[assignment]
        db.flush()
