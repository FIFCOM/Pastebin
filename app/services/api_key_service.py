"""
API Key服务层 - 业务逻辑处理
"""

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import generate_api_key, hash_api_key, verify_api_key
from app.core.time_utils import is_expired
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
)
from app.schemas.user import UserResponse


class ApiKeyService:
    """API密钥服务类"""

    _auth_cache: dict[str, int] = {}
    _auth_cache_max_entries = 4096

    @staticmethod
    def _cache_key(api_key: str) -> str:
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    @classmethod
    def _cache_get(cls, api_key: str) -> int | None:
        return cls._auth_cache.get(cls._cache_key(api_key))

    @classmethod
    def _cache_set(cls, api_key: str, api_key_id: int) -> None:
        if len(cls._auth_cache) >= cls._auth_cache_max_entries:
            cls._auth_cache.clear()
        cls._auth_cache[cls._cache_key(api_key)] = api_key_id

    @classmethod
    def _cache_clear(cls) -> None:
        cls._auth_cache.clear()

    @staticmethod
    def _build_key_preview(api_key: str) -> str:
        if len(api_key) <= 12:
            return api_key
        return f"{api_key[:6]}...{api_key[-4:]}"

    @staticmethod
    def _is_user_active(user: User) -> bool:
        value = getattr(user, "is_active", False)
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        return False

    @staticmethod
    def create_api_key(
        db: Session, user_id: int, api_key_data: ApiKeyCreateRequest
    ) -> ApiKeyCreateResponse:
        """
        创建API密钥

        Args:
            db: 数据库会话
            user_id: 用户ID
            api_key_data: API密钥创建数据

        Returns:
            创建的API密钥信息（包含明文密钥）

        Raises:
            ValueError: 当用户不存在时
        """
        # 验证用户是否存在
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise ValueError("用户不存在")
        if not ApiKeyService._is_user_active(user):
            raise ValueError("账户已被禁用")

        # 生成API密钥
        api_key_plain = generate_api_key()
        api_key_hash = hash_api_key(api_key_plain)
        key_preview = ApiKeyService._build_key_preview(api_key_plain)
        expires_at = (
            datetime.now(UTC) + timedelta(days=api_key_data.expires_in_days)
            if api_key_data.expires_in_days
            else None
        )

        # 创建API密钥记录
        api_key = ApiKey(
            user_id=user_id,
            name=api_key_data.name,
            key_hash=api_key_hash,
            key_preview=key_preview,
            expires_at=expires_at,
        )

        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        ApiKeyService._cache_clear()

        return ApiKeyCreateResponse(
            id=api_key.id,  # type: ignore
            name=api_key.name,  # type: ignore
            api_key=api_key_plain,  # 仅创建时返回明文密钥
            key_preview=api_key.key_preview,  # type: ignore
            created_at=api_key.created_at,  # type: ignore
            last_used_at=api_key.last_used_at,  # type: ignore
            last_used_ip=api_key.last_used_ip,  # type: ignore
            expires_at=api_key.expires_at,  # type: ignore
        )

    @staticmethod
    def get_user_api_keys(db: Session, user_id: int) -> ApiKeyListResponse:
        """
        获取用户的所有API密钥

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            API密钥列表（不包含密钥本身）
        """
        api_keys = (
            db.query(ApiKey)
            .filter(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc(), ApiKey.id.desc())
            .all()
        )

        return ApiKeyListResponse(
            api_keys=[
                ApiKeyResponse.model_validate(api_key)  # type: ignore
                for api_key in api_keys
            ]
        )

    @staticmethod
    def delete_api_key(db: Session, user_id: int, key_id: int) -> bool:
        """
        删除API密钥

        Args:
            db: 数据库会话
            user_id: 用户ID
            key_id: API密钥ID

        Returns:
            是否删除成功
        """
        api_key = (
            db.query(ApiKey)
            .filter(ApiKey.id == key_id, ApiKey.user_id == user_id)
            .first()
        )

        if api_key is None:
            return False

        db.delete(api_key)
        db.commit()
        ApiKeyService._cache_clear()
        return True

    @staticmethod
    def authenticate_api_key(
        db: Session,
        api_key: str,
        *,
        ip_address: str | None = None,
    ) -> UserResponse | None:
        """
        通过API密钥认证用户

        Args:
            db: 数据库会话
            api_key: API密钥明文

        Returns:
            认证成功的用户信息或None
        """
        preview = ApiKeyService._build_key_preview(api_key)

        cached_api_key_id = ApiKeyService._cache_get(api_key)
        if cached_api_key_id is not None:
            cached = db.query(ApiKey).filter(ApiKey.id == cached_api_key_id).first()
            if cached is not None and verify_api_key(api_key, str(cached.key_hash)):
                if is_expired(cached.expires_at):  # type: ignore[arg-type]
                    return None

                user = db.query(User).filter(User.id == cached.user_id).first()
                if user is not None:
                    if not ApiKeyService._is_user_active(user):
                        return None
                    cached.last_used_at = datetime.now(UTC)  # type: ignore[assignment]
                    if ip_address is not None:
                        cached.last_used_ip = ip_address  # type: ignore[assignment]
                    db.commit()
                    return UserResponse.model_validate(user)  # type: ignore

        api_keys = db.query(ApiKey).filter(ApiKey.key_preview == preview).all()

        if not api_keys:
            api_keys = db.query(ApiKey).filter(ApiKey.key_preview.is_(None)).all()

        for stored_api_key in api_keys:
            if verify_api_key(api_key, str(stored_api_key.key_hash)):
                if is_expired(stored_api_key.expires_at):  # type: ignore[arg-type]
                    return None

                if stored_api_key.key_preview is None:
                    stored_api_key.key_preview = preview  # type: ignore[assignment]

                # 找到匹配的API密钥，返回对应用户
                user = db.query(User).filter(User.id == stored_api_key.user_id).first()
                if user is not None:
                    if not ApiKeyService._is_user_active(user):
                        return None
                    stored_api_key.last_used_at = datetime.now(UTC)  # type: ignore[assignment]
                    if ip_address is not None:
                        stored_api_key.last_used_ip = ip_address  # type: ignore[assignment]
                    db.commit()
                    api_key_id = getattr(stored_api_key, "id", None)
                    if isinstance(api_key_id, int):
                        ApiKeyService._cache_set(api_key, api_key_id)
                    return UserResponse.model_validate(user)  # type: ignore
                break

        return None

    @staticmethod
    def get_api_key_by_id(
        db: Session, user_id: int, key_id: int
    ) -> ApiKeyResponse | None:
        """
        根据ID获取API密钥信息

        Args:
            db: 数据库会话
            user_id: 用户ID
            key_id: API密钥ID

        Returns:
            API密钥信息或None
        """
        api_key = (
            db.query(ApiKey)
            .filter(ApiKey.id == key_id, ApiKey.user_id == user_id)
            .first()
        )

        if not api_key:
            return None

        return ApiKeyResponse.model_validate(api_key)  # type: ignore
