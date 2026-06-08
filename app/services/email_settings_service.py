"""
邮箱验证配置服务
"""

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.security import (
    bytes_to_str,
    decrypt_with_key,
    encrypt_with_key,
    str_to_bytes,
)
from app.models.email_verification import EmailVerificationSetting
from app.schemas.email_settings import (
    EmailVerificationSettingsResponse,
    EmailVerificationSettingsUpdateRequest,
)
from config.config import settings


def _smtp_secret_key() -> bytes:
    return hashlib.sha256(
        f"{settings.secret_key}:email-verification-smtp-password".encode()
    ).digest()


class EmailSettingsService:
    """邮箱验证配置读写。"""

    @staticmethod
    def ensure_default(db: Session, *, commit: bool = True) -> EmailVerificationSetting:
        row = db.query(EmailVerificationSetting).filter(EmailVerificationSetting.id == 1).first()
        if row is None:
            row = EmailVerificationSetting(id=1)
            db.add(row)
            if commit:
                db.commit()
                db.refresh(row)
            else:
                db.flush()
        return row

    @staticmethod
    def _encrypt_password(password: str) -> str:
        encrypted = encrypt_with_key(password.encode("utf-8"), _smtp_secret_key())
        return bytes_to_str(encrypted)

    @staticmethod
    def decrypt_password(row: EmailVerificationSetting) -> str | None:
        encrypted = row.smtp_password_encrypted
        if not encrypted:
            return None
        try:
            plaintext = decrypt_with_key(str_to_bytes(str(encrypted)), _smtp_secret_key())
            return plaintext.decode("utf-8")
        except Exception as e:
            raise ValueError("SMTP密码解密失败，请重新配置SMTP密码") from e

    @staticmethod
    def _response(row: EmailVerificationSetting) -> EmailVerificationSettingsResponse:
        return EmailVerificationSettingsResponse(
            enabled=bool(row.enabled),
            smtp_host=str(row.smtp_host).strip() if row.smtp_host else None,
            smtp_port=int(row.smtp_port or 587),
            smtp_security=str(row.smtp_security or "starttls"),  # type: ignore[arg-type]
            smtp_username=str(row.smtp_username).strip() if row.smtp_username else None,
            smtp_password_configured=bool(row.smtp_password_encrypted),
            smtp_from_email=str(row.smtp_from_email).strip()
            if row.smtp_from_email
            else None,
            smtp_from_name=str(row.smtp_from_name or "Material Bin"),
            code_ttl_minutes=int(row.code_ttl_minutes or 10),
            resend_interval_seconds=int(row.resend_interval_seconds or 60),
            max_attempts=int(row.max_attempts or 5),
        )

    @staticmethod
    def get_settings(db: Session) -> EmailVerificationSetting:
        return EmailSettingsService.ensure_default(db)

    @staticmethod
    def get_settings_response(db: Session) -> EmailVerificationSettingsResponse:
        return EmailSettingsService._response(EmailSettingsService.get_settings(db))

    @staticmethod
    def is_enabled(db: Session) -> bool:
        return bool(EmailSettingsService.get_settings(db).enabled)

    @staticmethod
    def update_settings(
        db: Session,
        payload: EmailVerificationSettingsUpdateRequest,
        *,
        updated_by: int | None,
    ) -> EmailVerificationSettingsResponse:
        row = EmailSettingsService.ensure_default(db, commit=False)

        smtp_host = payload.smtp_host.strip() if payload.smtp_host else None
        smtp_from_email = (
            str(payload.smtp_from_email).strip() if payload.smtp_from_email else None
        )
        smtp_username = (
            payload.smtp_username.strip() if payload.smtp_username else None
        )

        if payload.enabled:
            if not smtp_host:
                raise ValueError("启用邮箱验证码前请填写SMTP服务器")
            if not smtp_from_email:
                raise ValueError("启用邮箱验证码前请填写发件邮箱")

        row.enabled = payload.enabled  # type: ignore[assignment]
        row.smtp_host = smtp_host  # type: ignore[assignment]
        row.smtp_port = payload.smtp_port  # type: ignore[assignment]
        row.smtp_security = payload.smtp_security  # type: ignore[assignment]
        row.smtp_username = smtp_username  # type: ignore[assignment]
        row.smtp_from_email = smtp_from_email  # type: ignore[assignment]
        row.smtp_from_name = payload.smtp_from_name.strip()  # type: ignore[assignment]
        row.code_ttl_minutes = payload.code_ttl_minutes  # type: ignore[assignment]
        row.resend_interval_seconds = payload.resend_interval_seconds  # type: ignore[assignment]
        row.max_attempts = payload.max_attempts  # type: ignore[assignment]
        row.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        row.updated_by = updated_by  # type: ignore[assignment]

        if payload.clear_smtp_password:
            row.smtp_password_encrypted = None  # type: ignore[assignment]
        elif payload.smtp_password is not None:
            row.smtp_password_encrypted = EmailSettingsService._encrypt_password(
                payload.smtp_password
            )  # type: ignore[assignment]

        db.commit()
        db.refresh(row)
        return EmailSettingsService._response(row)
