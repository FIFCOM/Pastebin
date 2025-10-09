"""
API Key服务层 - 业务逻辑处理
"""

from sqlalchemy.orm import Session

from app.core.security import generate_api_key, hash_api_key, verify_api_key
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
        if not user:
            raise ValueError("用户不存在")

        # 生成API密钥
        api_key_plain = generate_api_key()
        api_key_hash = hash_api_key(api_key_plain)

        # 创建API密钥记录
        api_key = ApiKey(
            user_id=user_id,
            name=api_key_data.name,
            key_hash=api_key_hash,
        )

        db.add(api_key)
        db.commit()
        db.refresh(api_key)

        return ApiKeyCreateResponse(
            id=api_key.id,  # type: ignore
            name=api_key.name,  # type: ignore
            api_key=api_key_plain,  # 仅创建时返回明文密钥
            created_at=api_key.created_at,  # type: ignore
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
        api_keys = db.query(ApiKey).filter(ApiKey.user_id == user_id).all()

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

        if not api_key:
            return False

        db.delete(api_key)
        db.commit()
        return True

    @staticmethod
    def authenticate_api_key(db: Session, api_key: str) -> UserResponse | None:
        """
        通过API密钥认证用户

        Args:
            db: 数据库会话
            api_key: API密钥明文

        Returns:
            认证成功的用户信息或None
        """
        # 查找所有API密钥，逐一验证（因为我们存储的是哈希值）
        api_keys = db.query(ApiKey).all()

        for stored_api_key in api_keys:
            if verify_api_key(api_key, str(stored_api_key.key_hash)):
                # 找到匹配的API密钥，返回对应用户
                user = db.query(User).filter(User.id == stored_api_key.user_id).first()
                if user:
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
