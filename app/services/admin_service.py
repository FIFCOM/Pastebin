"""
管理员后台服务层
"""

from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.collab_room import Member
from app.models.paste import File, FileUploadSession, Paste
from app.models.user import UsedRefreshToken, User, UserSession
from app.schemas.admin import (
    AdminCleanupStatusResponse,
    AdminOverviewResponse,
    AdminPasteListItem,
    AdminPasteListResponse,
    CleanupTaskName,
)
from app.services.paste_service import PasteService
from config.config import settings

PASTE_STATUSES = {"draft", "published", "edited"}
PASTE_TYPES = {"txt", "md"}
PASTE_ENCRYPTION_MODES = {"client", "server"}

SUPPORTED_CLEANUP_TASKS: list[CleanupTaskName] = [
    "expired_drafts",
    "expired_pastes",
    "expired_uploads",
    "expired_members",
    "expired_user_sessions",
    "expired_used_refresh_tokens",
]


class AdminService:
    """管理员后台服务类"""

    @staticmethod
    def _cleanup_counts(db: Session) -> dict[CleanupTaskName, int]:
        now = datetime.now(UTC)
        used_refresh_cutoff = now - timedelta(days=settings.refresh_token_expire_days)

        return {
            "expired_drafts": db.query(Paste)
            .filter(Paste.status == "draft", Paste.expire_at < now)
            .count(),
            "expired_pastes": db.query(Paste)
            .filter(
                Paste.status.in_(["published", "edited"]),
                Paste.expire_at.isnot(None),
                Paste.expire_at < now,
            )
            .count(),
            "expired_uploads": db.query(FileUploadSession)
            .filter(FileUploadSession.expire_at < now)
            .count(),
            "expired_members": db.query(Member).filter(Member.expire_at < now).count(),
            "expired_user_sessions": db.query(UserSession)
            .filter(UserSession.expires_at < now)
            .count(),
            "expired_used_refresh_tokens": db.query(UsedRefreshToken)
            .filter(UsedRefreshToken.used_at < used_refresh_cutoff)
            .count(),
        }

    @staticmethod
    def get_overview(db: Session) -> AdminOverviewResponse:
        total_storage = db.query(func.coalesce(func.sum(File.file_size), 0)).scalar()
        total_views = db.query(func.coalesce(func.sum(Paste.view_count), 0)).scalar()

        return AdminOverviewResponse(
            total_users=db.query(User).count(),
            active_users=db.query(User).filter(User.is_active.is_(True)).count(),
            total_pastes=db.query(Paste).count(),
            total_files=db.query(File).count(),
            total_storage_bytes=int(total_storage or 0),
            total_view_count=int(total_views or 0),
            cleanup_counts=AdminService._cleanup_counts(db),
        )

    @staticmethod
    def get_cleanup_status(db: Session) -> AdminCleanupStatusResponse:
        return AdminCleanupStatusResponse(
            supported_tasks=SUPPORTED_CLEANUP_TASKS,
            cleanup_counts=AdminService._cleanup_counts(db),
        )

    @staticmethod
    def list_pastes(
        db: Session,
        page: int,
        size: int,
        search: str | None = None,
        status: Literal["draft", "published", "edited"] | None = None,
        paste_type: Literal["txt", "md"] | None = None,
        encryption_mode: Literal["client", "server"] | None = None,
    ) -> AdminPasteListResponse:
        file_stats = (
            db.query(
                File.paste_id.label("paste_id"),
                func.count(File.id).label("file_count"),
                func.coalesce(func.sum(File.file_size), 0).label("file_total_size"),
            )
            .group_by(File.paste_id)
            .subquery()
        )

        query = db.query(
            Paste,
            file_stats.c.file_count,
            file_stats.c.file_total_size,
            User.username.label("creator_username"),
        )
        query = query.outerjoin(file_stats, Paste.id == file_stats.c.paste_id)
        query = query.outerjoin(User, Paste.creator_user_id == User.id)

        if search:
            search_text = search.strip()
            search_pattern = f"%{search_text}%"
            search_filters = [
                Paste.id.ilike(search_pattern),
                Paste.title.ilike(search_pattern),
                User.username.ilike(search_pattern),
                Paste.creator_ip.ilike(search_pattern),
            ]
            if search_text.isdigit():
                search_filters.append(Paste.creator_user_id == int(search_text))
            query = query.filter(or_(*search_filters))

        if status:
            query = query.filter(Paste.status == status)

        if paste_type:
            query = query.filter(Paste.type == paste_type)

        if encryption_mode:
            query = query.filter(Paste.encryption_mode == encryption_mode)

        total = query.count()
        rows = (
            query.order_by(Paste.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )

        items: list[AdminPasteListItem] = []
        for paste, file_count, file_total_size, creator_username in rows:
            items.append(
                AdminPasteListItem(
                    id=str(paste.id),
                    title=str(paste.title) if paste.title else None,
                    status=str(paste.status),  # type: ignore[arg-type]
                    type=str(paste.type or "txt"),  # type: ignore[arg-type]
                    encryption_mode=str(paste.encryption_mode or "client"),  # type: ignore[arg-type]
                    creator_type=str(paste.creator_type or "guest"),  # type: ignore[arg-type]
                    creator_user_id=paste.creator_user_id,  # type: ignore[arg-type]
                    creator_username=(
                        str(creator_username) if creator_username else None
                    ),
                    creator_ip=str(paste.creator_ip) if paste.creator_ip else None,
                    view_count=int(paste.view_count or 0),
                    max_views=int(paste.max_views or -1),
                    file_count=int(file_count or 0),
                    file_total_size=int(file_total_size or 0),
                    created_at=paste.created_at,  # type: ignore[arg-type]
                    updated_at=paste.updated_at,  # type: ignore[arg-type]
                    published_at=paste.published_at,  # type: ignore[arg-type]
                    expire_at=paste.expire_at,  # type: ignore[arg-type]
                )
            )

        return AdminPasteListResponse(
            pastes=items,
            total=total,
            page=page,
            size=size,
        )

    @staticmethod
    def delete_paste(db: Session, paste_id: str) -> bool:
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            return False

        PasteService.delete_paste_record(db, paste)
        db.commit()
        return True
