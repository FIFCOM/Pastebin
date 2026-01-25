"""
用户History管理服务层 - 业务逻辑处理
"""

from sqlalchemy.orm import Session, joinedload

from app.core.security import (
    bytes_to_str,
    decrypt_with_key,
    encrypt_with_key,
    key_to_urlsafe_str,
    str_to_bytes,
    urlsafe_str_to_key,
)
from app.models.paste import Paste
from app.models.user_history import UserHistory
from app.schemas.user_history import (
    UserHistoryInfo,
    UserHistoryListResponse,
    UserHistorySaveRequest,
    UserHistorySearchParams,
    UserHistoryStarRequest,
)
from app.services.paste_service import PasteService


class UserHistoryService:
    """用户History管理服务类"""

    @staticmethod
    def _encrypt_paste_key_for_user(paste_key: str, user_key: bytes) -> str:
        """使用用户密钥加密paste密钥（paste_key是URL-safe格式）"""
        paste_key_bytes = urlsafe_str_to_key(paste_key)
        encrypted_paste_key = encrypt_with_key(paste_key_bytes, user_key)
        return bytes_to_str(encrypted_paste_key)

    @staticmethod
    def _decrypt_paste_key_for_user(encrypted_paste_key: str, user_key: bytes) -> str:
        """使用用户密钥解密paste密钥（返回URL-safe格式）"""
        encrypted_paste_key_bytes = str_to_bytes(encrypted_paste_key)
        decrypted_paste_key = decrypt_with_key(encrypted_paste_key_bytes, user_key)
        return key_to_urlsafe_str(decrypted_paste_key)

    @staticmethod
    def save_paste_to_history(
        db: Session,
        user_id: int,
        paste_id: str,
        user_key: bytes,
        save_request: UserHistorySaveRequest,
    ) -> None:
        """
        将Paste保存到用户账户

        Args:
            db: 数据库会话
            user_id: 用户ID
            paste_id: Paste ID
            user_key: 用户密钥（用于加密paste密钥）
            save_request: 保存请求数据

        Raises:
            ValueError: 当验证失败时
        """
        # 验证Paste是否存在
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")

        # 验证admin_key权限
        if not PasteService._verify_admin_key(paste, save_request.admin_key):
            raise ValueError("管理权限验证失败")

        # 检查是否已经保存过
        existing_user_history = (
            db.query(UserHistory)
            .filter(UserHistory.user_id == user_id, UserHistory.paste_id == paste_id)
            .first()
        )
        if existing_user_history:
            raise ValueError("该Paste已保存到用户账户")

        # 使用用户密钥加密paste密钥
        encrypted_paste_key = UserHistoryService._encrypt_paste_key_for_user(
            save_request.encryption_key, user_key
        )

        # 创建UserHistory记录
        user_history = UserHistory(
            user_id=user_id,
            paste_id=paste_id,
            encrypted_paste_key=encrypted_paste_key,
            is_starred=False,
        )

        db.add(user_history)
        db.commit()

    @staticmethod
    def get_user_history(
        db: Session,
        user_id: int,
        user_key: bytes,
        search_params: UserHistorySearchParams,
    ) -> UserHistoryListResponse:
        """
        获取用户的所有Paste

        Args:
            db: 数据库会话
            user_id: 用户ID
            user_key: 用户密钥（用于解密paste密钥）
            search_params: 搜索参数

        Returns:
            用户Paste列表响应
        """
        # 构建基础查询
        query = (
            db.query(UserHistory)
            .join(Paste, UserHistory.paste_id == Paste.id)
            .filter(UserHistory.user_id == user_id)
            .options(joinedload(UserHistory.paste))
        )

        # 状态过滤
        if search_params.status and search_params.status != "all":
            query = query.filter(Paste.status == search_params.status)

        # 收藏状态过滤
        if search_params.starred is not None:
            query = query.filter(UserHistory.is_starred == search_params.starred)

        # 搜索关键词过滤
        if search_params.search:
            search_term = f"%{search_params.search}%"
            query = query.filter(Paste.title.ilike(search_term))

        # 计算总数
        total = query.count()

        # 分页
        offset = (search_params.page - 1) * search_params.limit
        user_history_list = (
            query.order_by(UserHistory.created_at.desc())
            .offset(offset)
            .limit(search_params.limit)
            .all()
        )

        # 构建响应数据
        paste_infos = []
        for user_history in user_history_list:
            paste = user_history.paste

            # 解密paste密钥
            try:
                decrypted_paste_key = UserHistoryService._decrypt_paste_key_for_user(
                    str(user_history.encrypted_paste_key),
                    user_key,  # type: ignore
                )
            except Exception:
                # 如果解密失败，跳过这个paste或使用空字符串
                decrypted_paste_key = ""

            paste_info = UserHistoryInfo(
                paste_id=str(paste.id),  # type: ignore
                status=str(paste.status),  # type: ignore
                title=str(paste.title) if paste.title else None,  # type: ignore
                admin_key=str(paste.admin_key),  # type: ignore
                encryption_key=decrypted_paste_key,
                max_views=int(paste.max_views or -1),  # type: ignore
                view_count=int(paste.view_count or 0),  # type: ignore
                is_starred=bool(user_history.is_starred),  # type: ignore
                published_at=paste.published_at,  # type: ignore
                updated_at=paste.updated_at,  # type: ignore
                expire_at=paste.expire_at,  # type: ignore
            )
            paste_infos.append(paste_info)

        return UserHistoryListResponse(
            pastes=paste_infos,
            total=total,
            page=search_params.page,
            limit=search_params.limit,
        )

    @staticmethod
    def update_history_star_status(
        db: Session,
        user_id: int,
        paste_id: str,
        star_request: UserHistoryStarRequest,
    ) -> None:
        """
        更新Paste收藏状态

        Args:
            db: 数据库会话
            user_id: 用户ID
            paste_id: Paste ID
            star_request: 收藏状态请求

        Raises:
            ValueError: 当UserHistory不存在时
        """
        user_history = (
            db.query(UserHistory)
            .filter(UserHistory.user_id == user_id, UserHistory.paste_id == paste_id)
            .first()
        )

        if not user_history:
            raise ValueError("该Paste未保存到用户账户")

        user_history.is_starred = star_request.is_starred  # type: ignore
        db.commit()

    @staticmethod
    def remove_paste_from_history(
        db: Session,
        user_id: int,
        paste_id: str,
    ) -> None:
        """
        从用户账户移除Paste

        Args:
            db: 数据库会话
            user_id: 用户ID
            paste_id: Paste ID

        Raises:
            ValueError: 当UserHistory不存在时
        """
        user_history = (
            db.query(UserHistory)
            .filter(UserHistory.user_id == user_id, UserHistory.paste_id == paste_id)
            .first()
        )

        if not user_history:
            raise ValueError("该Paste未保存到用户账户")

        db.delete(user_history)
        db.commit()

    @staticmethod
    def get_user_history_item(
        db: Session,
        user_id: int,
        paste_id: str,
        user_key: bytes,
    ) -> UserHistoryInfo | None:
        """
        获取单个用户History信息

        Args:
            db: 数据库会话
            user_id: 用户ID
            paste_id: Paste ID
            user_key: 用户密钥

        Returns:
            用户History信息或None
        """
        user_history = (
            db.query(UserHistory)
            .join(Paste, UserHistory.paste_id == Paste.id)
            .filter(UserHistory.user_id == user_id, UserHistory.paste_id == paste_id)
            .options(joinedload(UserHistory.paste))
            .first()
        )

        if not user_history:
            return None

        paste = user_history.paste

        # 解密paste密钥
        try:
            decrypted_paste_key = UserHistoryService._decrypt_paste_key_for_user(
                str(user_history.encrypted_paste_key),
                user_key,  # type: ignore
            )
        except Exception:
            decrypted_paste_key = ""

        return UserHistoryInfo(
            paste_id=str(paste.id),  # type: ignore
            status=str(paste.status),  # type: ignore
            title=str(paste.title) if paste.title else None,  # type: ignore
            admin_key=str(paste.admin_key),  # type: ignore
            encryption_key=decrypted_paste_key,
            max_views=int(paste.max_views or -1),  # type: ignore
            view_count=int(paste.view_count or 0),  # type: ignore
            is_starred=bool(user_history.is_starred),  # type: ignore
            published_at=paste.published_at,  # type: ignore
            updated_at=paste.updated_at,  # type: ignore
            expire_at=paste.expire_at,  # type: ignore
        )
