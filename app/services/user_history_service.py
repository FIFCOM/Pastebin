"""
用户History管理服务层 - 业务逻辑处理
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
from app.models.user_history import UserHistory
from app.schemas.user_history import (
    GuestHistoryItem,
    ImportGuestHistoryRequest,
    ImportGuestHistoryResponse,
    UserHistoryDetail,
    UserHistoryListItem,
    UserHistoryListResponse,
    UserHistorySaveRequest,
    UserHistorySearchParams,
)
from app.services.paste_service import PasteService

# 游客导入上限
IMPORT_GUEST_MAX_ITEMS = 500
logger = logging.getLogger(__name__)


class UserHistoryService:
    """用户History管理服务类"""

    @staticmethod
    def _encrypt_key_for_user(key_str: str, user_key: bytes) -> str:
        """使用用户密钥加密URL-safe格式的密钥字符串"""
        key_bytes = urlsafe_str_to_key(key_str, expected_length=None)
        encrypted = encrypt_with_key(key_bytes, user_key)
        return bytes_to_str(encrypted)

    @staticmethod
    def _decrypt_key_for_user(encrypted_key_str: str, user_key: bytes) -> str:
        """使用用户密钥解密，返回URL-safe格式的密钥字符串"""
        encrypted_bytes = str_to_bytes(encrypted_key_str)
        decrypted = decrypt_with_key(encrypted_bytes, user_key)
        return key_to_urlsafe_str(decrypted)

    @staticmethod
    def _encrypt_admin_key_for_user(admin_key: str, user_key: bytes) -> str:
        """使用用户密钥加密admin_key（admin_key是普通字符串）"""
        admin_key_bytes = admin_key.encode("utf-8")
        encrypted = encrypt_with_key(admin_key_bytes, user_key)
        return bytes_to_str(encrypted)

    @staticmethod
    def _decrypt_admin_key_for_user(
        encrypted_admin_key_str: str, user_key: bytes
    ) -> str:
        """使用用户密钥解密admin_key"""
        encrypted_bytes = str_to_bytes(encrypted_admin_key_str)
        decrypted = decrypt_with_key(encrypted_bytes, user_key)
        return decrypted.decode("utf-8")

    @staticmethod
    def _build_list_item(user_history: UserHistory) -> UserHistoryListItem:
        """从 UserHistory ORM 对象构建列表条目（不含明文密钥）"""
        paste = user_history.paste
        return UserHistoryListItem(
            paste_id=str(paste.id),
            status=str(paste.status),
            title=str(paste.title) if paste.title else None,
            max_views=int(paste.max_views or -1),
            view_count=int(paste.view_count or 0),
            published_at=paste.published_at,
            paste_updated_at=paste.updated_at,
            history_updated_at=cast(datetime, cast(object, user_history.updated_at)),
            expire_at=paste.expire_at,
        )

    @staticmethod
    def _upsert_history(
        db: Session,
        user_id: int,
        paste_id: str,
        user_key: bytes,
        admin_key: str,
        encryption_key: str,
    ) -> UserHistory:
        """
        原子 upsert：不存在则插入，存在则更新密文并恢复软删除。
        返回最终的 UserHistory 记录。
        """
        encrypted_paste_key = UserHistoryService._encrypt_key_for_user(
            encryption_key, user_key
        )
        encrypted_admin_key = UserHistoryService._encrypt_admin_key_for_user(
            admin_key, user_key
        )
        now = datetime.now(UTC)

        # 先尝试查找已有记录（含软删除）
        existing = (
            db.query(UserHistory)
            .filter(
                UserHistory.user_id == user_id,
                UserHistory.paste_id == paste_id,
            )
            .first()
        )

        if existing:
            set_attribute(existing, "encrypted_paste_key", encrypted_paste_key)
            set_attribute(existing, "encrypted_admin_key", encrypted_admin_key)
            set_attribute(existing, "is_deleted", False)
            set_attribute(existing, "updated_at", now)
            db.commit()
            db.refresh(existing)
            return existing

        # 不存在，尝试插入；并发下可能触发 IntegrityError
        record = UserHistory(
            user_id=user_id,
            paste_id=paste_id,
            encrypted_paste_key=encrypted_paste_key,
            encrypted_admin_key=encrypted_admin_key,
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
            # 并发插入冲突，回退到更新
            existing = (
                db.query(UserHistory)
                .filter(
                    UserHistory.user_id == user_id,
                    UserHistory.paste_id == paste_id,
                )
                .first()
            )
            if existing is None:
                raise
            set_attribute(existing, "encrypted_paste_key", encrypted_paste_key)
            set_attribute(existing, "encrypted_admin_key", encrypted_admin_key)
            set_attribute(existing, "is_deleted", False)
            set_attribute(existing, "updated_at", now)
            db.commit()
            db.refresh(existing)
            return existing

    @staticmethod
    def save_paste_to_history(
        db: Session,
        user_id: int,
        paste_id: str,
        user_key: bytes,
        save_request: UserHistorySaveRequest,
    ) -> None:
        """
        将Paste保存到用户账户（upsert）

        Raises:
            ValueError: 当验证失败时
        """
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")

        if not PasteService._verify_admin_key(paste, save_request.admin_key):
            raise ValueError("管理权限验证失败")

        _ = UserHistoryService._upsert_history(
            db,
            user_id,
            paste_id,
            user_key,
            save_request.admin_key,
            save_request.encryption_key,
        )

    @staticmethod
    def get_user_history(
        db: Session,
        user_id: int,
        search_params: UserHistorySearchParams,
    ) -> UserHistoryListResponse:
        """获取用户的历史记录列表（不含明文密钥）"""
        query = (
            db.query(UserHistory)
            .join(Paste, UserHistory.paste_id == Paste.id)
            .filter(
                UserHistory.user_id == user_id,
                UserHistory.is_deleted == False,  # noqa: E712
            )
            .options(joinedload(UserHistory.paste))
        )

        if search_params.search:
            search_term = f"%{search_params.search}%"
            query = query.filter(Paste.title.ilike(search_term))

        total = query.count()

        offset = (search_params.page - 1) * search_params.limit
        records = (
            query.order_by(UserHistory.updated_at.desc())
            .offset(offset)
            .limit(search_params.limit)
            .all()
        )

        items = [UserHistoryService._build_list_item(r) for r in records]

        return UserHistoryListResponse(
            items=items,
            total=total,
            page=search_params.page,
            limit=search_params.limit,
        )

    @staticmethod
    def get_user_history_detail(
        db: Session,
        user_id: int,
        paste_id: str,
        user_key: bytes,
    ) -> UserHistoryDetail | None:
        """获取单条历史详情（含解密后的密钥）"""
        record = (
            db.query(UserHistory)
            .join(Paste, UserHistory.paste_id == Paste.id)
            .filter(
                UserHistory.user_id == user_id,
                UserHistory.paste_id == paste_id,
                UserHistory.is_deleted == False,  # noqa: E712
            )
            .options(joinedload(UserHistory.paste))
            .first()
        )

        if not record:
            return None

        paste = record.paste

        try:
            decrypted_paste_key = UserHistoryService._decrypt_key_for_user(
                str(record.encrypted_paste_key), user_key
            )
        except Exception as e:
            raise ValueError(
                "历史记录密钥解密失败，可能存在数据损坏或用户密钥不匹配"
            ) from e

        try:
            decrypted_admin_key = UserHistoryService._decrypt_admin_key_for_user(
                str(record.encrypted_admin_key), user_key
            )
        except Exception as e:
            raise ValueError(
                "历史记录管理密钥解密失败，可能存在数据损坏或用户密钥不匹配"
            ) from e

        return UserHistoryDetail(
            paste_id=str(paste.id),
            status=str(paste.status),
            title=str(paste.title) if paste.title else None,
            admin_key=decrypted_admin_key,
            encryption_key=decrypted_paste_key,
            max_views=int(paste.max_views or -1),
            view_count=int(paste.view_count or 0),
            published_at=paste.published_at,
            paste_updated_at=paste.updated_at,
            history_updated_at=cast(datetime, cast(object, record.updated_at)),
            expire_at=paste.expire_at,
        )

    @staticmethod
    def soft_delete_history(
        db: Session,
        user_id: int,
        paste_id: str,
    ) -> None:
        """软删除历史记录"""
        record = (
            db.query(UserHistory)
            .filter(
                UserHistory.user_id == user_id,
                UserHistory.paste_id == paste_id,
            )
            .first()
        )

        if not record:
            raise ValueError("该Paste未保存到用户账户")

        set_attribute(record, "is_deleted", True)
        set_attribute(record, "updated_at", datetime.now(UTC))
        db.commit()

    @staticmethod
    def import_guest_history(
        db: Session,
        user_id: int,
        user_key: bytes,
        request: ImportGuestHistoryRequest,
    ) -> ImportGuestHistoryResponse:
        """
        导入游客历史并合并到用户账户。
        允许部分成功，返回 imported/skipped 统计与失败原因摘要。
        """
        # 去重（按 pasteId）
        seen: set[str] = set()
        deduped: list[GuestHistoryItem] = []
        for item in request.items:
            if item.paste_id not in seen:
                seen.add(item.paste_id)
                deduped.append(item)

        # 上限保护
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
                        "导入游客历史校验失败 user_id=%s paste_id=%s reason=paste_not_found",
                        user_id,
                        item.paste_id,
                    )
                    errors.append(f"{item.paste_id}: 校验失败")
                    continue

                if not PasteService._verify_admin_key(paste, item.admin_key):
                    skipped += 1
                    logger.warning(
                        "导入游客历史校验失败 user_id=%s paste_id=%s reason=admin_key_invalid",
                        user_id,
                        item.paste_id,
                    )
                    errors.append(f"{item.paste_id}: 校验失败")
                    continue

                _ = UserHistoryService._upsert_history(
                    db,
                    user_id,
                    item.paste_id,
                    user_key,
                    item.admin_key,
                    item.encryption_key,
                )
                imported += 1
                imported_ids.append(item.paste_id)
            except Exception as e:
                skipped += 1
                logger.exception(
                    "导入游客历史失败 user_id=%s paste_id=%s error=%s",
                    user_id,
                    item.paste_id,
                    str(e),
                )
                errors.append(f"{item.paste_id}: 导入失败")

        # 返回最新快照（第一页）
        snapshot = UserHistoryService.get_user_history(
            db,
            user_id,
            UserHistorySearchParams(page=1, limit=50),
        )

        return ImportGuestHistoryResponse(
            imported=imported,
            imported_ids=imported_ids,
            skipped=skipped,
            errors=errors[:20],  # 最多返回20条错误摘要
            snapshot=snapshot,
        )
