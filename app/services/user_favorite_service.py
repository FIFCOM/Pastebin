"""
用户收藏Paste服务层 - 业务逻辑处理
"""

import logging
from datetime import UTC, datetime
from typing import cast

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import set_attribute

from app.core.security import (
    bytes_to_str,
    decrypt_with_key,
    encrypt_with_key,
    key_to_urlsafe_str,
    str_to_bytes,
    urlsafe_str_to_key,
)
from app.models.paste import Paste
from app.models.user_favorite import UserFavorite
from app.schemas.user_favorite import (
    GuestFavoriteItem,
    ImportGuestFavoritesRequest,
    ImportGuestFavoritesResponse,
    UserFavoriteDetail,
    UserFavoriteListItem,
    UserFavoriteListResponse,
    UserFavoriteSaveRequest,
    UserFavoriteSearchParams,
)
from app.services.paste_service import PasteService

# 游客导入上限
IMPORT_GUEST_MAX_ITEMS = 500
logger = logging.getLogger(__name__)


class UserFavoriteService:
    """用户收藏Paste服务类"""

    @staticmethod
    def _encrypt_key_for_user(encryption_key: str, user_key: bytes) -> str:
        """使用用户密钥加密URL-safe格式的paste解密密钥。"""
        key_bytes = urlsafe_str_to_key(encryption_key, expected_length=None)
        encrypted = encrypt_with_key(key_bytes, user_key)
        return bytes_to_str(encrypted)

    @staticmethod
    def _decrypt_key_for_user(encrypted_key: str, user_key: bytes) -> str:
        """使用用户密钥解密paste密钥，返回URL-safe格式字符串。"""
        encrypted_bytes = str_to_bytes(encrypted_key)
        decrypted = decrypt_with_key(encrypted_bytes, user_key)
        return key_to_urlsafe_str(decrypted)

    @staticmethod
    def _build_list_item(user_favorite: UserFavorite) -> UserFavoriteListItem:
        """从 UserFavorite ORM 对象构建列表条目（不含明文密钥）"""
        paste = user_favorite.paste
        return UserFavoriteListItem(
            paste_id=str(paste.id),
            status=str(paste.status),
            title=str(paste.title) if paste.title else None,
            max_views=int(paste.max_views or -1),
            view_count=int(paste.view_count or 0),
            published_at=paste.published_at,
            paste_updated_at=paste.updated_at,
            favorite_updated_at=cast(datetime, cast(object, user_favorite.updated_at)),
            expire_at=paste.expire_at,
        )

    @staticmethod
    def _upsert_favorite(
        db: Session,
        user_id: int,
        paste_id: str,
        user_key: bytes,
        encryption_key: str,
    ) -> UserFavorite:
        """
        原子 upsert：不存在则插入，存在则更新密文并恢复软删除。
        返回最终的 UserFavorite 记录。
        """
        encrypted_paste_key = UserFavoriteService._encrypt_key_for_user(
            encryption_key, user_key
        )
        now = datetime.now(UTC)

        existing = (
            db.query(UserFavorite)
            .filter(
                UserFavorite.user_id == user_id,
                UserFavorite.paste_id == paste_id,
            )
            .first()
        )

        if existing:
            set_attribute(existing, "encrypted_paste_key", encrypted_paste_key)
            set_attribute(existing, "is_deleted", False)
            set_attribute(existing, "updated_at", now)
            db.commit()
            db.refresh(existing)
            return existing

        record = UserFavorite(
            user_id=user_id,
            paste_id=paste_id,
            encrypted_paste_key=encrypted_paste_key,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        try:
            db.commit()
            db.refresh(record)
            return record
        except IntegrityError:
            db.rollback()
            existing = (
                db.query(UserFavorite)
                .filter(
                    UserFavorite.user_id == user_id,
                    UserFavorite.paste_id == paste_id,
                )
                .first()
            )
            if existing is None:
                raise
            set_attribute(existing, "encrypted_paste_key", encrypted_paste_key)
            set_attribute(existing, "is_deleted", False)
            set_attribute(existing, "updated_at", now)
            db.commit()
            db.refresh(existing)
            return existing

    @staticmethod
    def save_favorite(
        db: Session,
        user_id: int,
        paste_id: str,
        user_key: bytes,
        save_request: UserFavoriteSaveRequest,
    ) -> None:
        """
        保存Paste收藏（upsert）。

        保存收藏按公开读取规则校验 Paste 可访问性；access_key 仅用于本次校验。
        不验证 encryption_key 是否能解密内容。
        """
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")
        _ = PasteService.validate_paste_read_access(paste, save_request.access_key)

        _ = UserFavoriteService._upsert_favorite(
            db,
            user_id,
            paste_id,
            user_key,
            save_request.encryption_key,
        )

    @staticmethod
    def get_user_favorites(
        db: Session,
        user_id: int,
        search_params: UserFavoriteSearchParams,
    ) -> UserFavoriteListResponse:
        """获取用户收藏列表（不含明文密钥）"""
        query = (
            db.query(UserFavorite)
            .join(Paste, UserFavorite.paste_id == Paste.id)
            .filter(
                UserFavorite.user_id == user_id,
                UserFavorite.is_deleted == False,  # noqa: E712
            )
            .options(joinedload(UserFavorite.paste))
        )

        if search_params.search:
            search_term = f"%{search_params.search}%"
            query = query.filter(Paste.title.ilike(search_term))

        total = query.count()

        offset = (search_params.page - 1) * search_params.limit
        records = (
            query.order_by(UserFavorite.updated_at.desc())
            .offset(offset)
            .limit(search_params.limit)
            .all()
        )

        items = [UserFavoriteService._build_list_item(r) for r in records]

        return UserFavoriteListResponse(
            items=items,
            total=total,
            page=search_params.page,
            limit=search_params.limit,
        )

    @staticmethod
    def get_user_favorite_detail(
        db: Session,
        user_id: int,
        paste_id: str,
        user_key: bytes,
    ) -> UserFavoriteDetail | None:
        """获取单条收藏详情（含解密后的paste密钥）"""
        record = (
            db.query(UserFavorite)
            .join(Paste, UserFavorite.paste_id == Paste.id)
            .filter(
                UserFavorite.user_id == user_id,
                UserFavorite.paste_id == paste_id,
                UserFavorite.is_deleted == False,  # noqa: E712
            )
            .options(joinedload(UserFavorite.paste))
            .first()
        )

        if not record:
            return None

        try:
            decrypted_paste_key = UserFavoriteService._decrypt_key_for_user(
                str(record.encrypted_paste_key), user_key
            )
        except Exception as e:
            raise ValueError(
                "收藏密钥解密失败，可能存在数据损坏或用户密钥不匹配"
            ) from e

        item = UserFavoriteService._build_list_item(record)
        return UserFavoriteDetail(
            **item.model_dump(),
            encryption_key=decrypted_paste_key,
        )

    @staticmethod
    def soft_delete_favorite(
        db: Session,
        user_id: int,
        paste_id: str,
    ) -> None:
        """软删除收藏记录"""
        record = (
            db.query(UserFavorite)
            .filter(
                UserFavorite.user_id == user_id,
                UserFavorite.paste_id == paste_id,
            )
            .first()
        )

        if not record:
            raise ValueError("该Paste未收藏")

        set_attribute(record, "is_deleted", True)
        set_attribute(record, "updated_at", datetime.now(UTC))
        db.commit()

    @staticmethod
    def import_guest_favorites(
        db: Session,
        user_id: int,
        user_key: bytes,
        request: ImportGuestFavoritesRequest,
    ) -> ImportGuestFavoritesResponse:
        """
        导入游客收藏并合并到用户账户。
        允许部分成功，返回 imported/skipped 统计与失败原因摘要。
        """
        seen: set[str] = set()
        deduped: list[GuestFavoriteItem] = []
        for item in request.items:
            if item.paste_id not in seen:
                seen.add(item.paste_id)
                deduped.append(item)

        overflow_count = max(0, len(deduped) - IMPORT_GUEST_MAX_ITEMS)
        deduped = deduped[:IMPORT_GUEST_MAX_ITEMS]

        imported = 0
        imported_ids: list[str] = []
        skipped = overflow_count
        errors: list[str] = []
        if overflow_count > 0:
            errors.append(f"超出导入上限，已跳过 {overflow_count} 条")

        for item in deduped:
            try:
                paste = db.query(Paste).filter(Paste.id == item.paste_id).first()
                if not paste:
                    skipped += 1
                    logger.warning(
                        "导入游客收藏校验失败 user_id=%s paste_id=%s reason=paste_not_found",
                        user_id,
                        item.paste_id,
                    )
                    errors.append(f"{item.paste_id}: Paste不存在")
                    continue

                _ = PasteService.validate_paste_read_access(paste, item.access_key)

                _ = UserFavoriteService._upsert_favorite(
                    db,
                    user_id,
                    item.paste_id,
                    user_key,
                    item.encryption_key,
                )
                imported += 1
                imported_ids.append(item.paste_id)
            except Exception as e:
                skipped += 1
                logger.exception(
                    "导入游客收藏失败 user_id=%s paste_id=%s error=%s",
                    user_id,
                    item.paste_id,
                    str(e),
                )
                errors.append(f"{item.paste_id}: 导入失败")

        snapshot = UserFavoriteService.get_user_favorites(
            db,
            user_id,
            UserFavoriteSearchParams(page=1, limit=50),
        )

        return ImportGuestFavoritesResponse(
            imported=imported,
            imported_ids=imported_ids,
            skipped=skipped,
            errors=errors[:20],
            snapshot=snapshot,
        )
