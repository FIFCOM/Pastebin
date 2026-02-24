"""
安装状态服务
"""

import time
from dataclasses import dataclass
from pathlib import Path
from threading import RLock

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.user import User

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
INSTALL_REQUIRED_CACHE_TTL_SECONDS = 5.0


@dataclass(frozen=True)
class InstallState:
    needs_install: bool
    env_exists: bool
    admin_exists: bool


class InstallStateService:
    _cache_lock = RLock()
    _cached_state: InstallState | None = None
    _cache_expire_monotonic: float | None = None

    @staticmethod
    def _query_install_state(db: Session) -> InstallState:
        env_exists = ENV_FILE.exists()
        # 未生成 .env 时不触发数据库连接，避免 SQLite 自动建库副作用
        if not env_exists:
            return InstallState(
                needs_install=True,
                env_exists=False,
                admin_exists=False,
            )

        try:
            has_user_table = inspect(db.get_bind()).has_table(User.__tablename__)
        except SQLAlchemyError:
            has_user_table = False

        if not has_user_table:
            return InstallState(
                needs_install=True,
                env_exists=True,
                admin_exists=False,
            )

        admin_exists = db.query(User.id).filter(User.role == "admin").first() is not None
        needs_install = (not env_exists) or (not admin_exists)
        return InstallState(
            needs_install=needs_install,
            env_exists=env_exists,
            admin_exists=admin_exists,
        )

    @classmethod
    def get_state(cls, db: Session, *, force_refresh: bool = False) -> InstallState:
        now = time.monotonic()
        with cls._cache_lock:
            cached = cls._cached_state
            if not force_refresh and cached is not None:
                if not cached.needs_install:
                    return cached
                if (
                    cls._cache_expire_monotonic is not None
                    and now < cls._cache_expire_monotonic
                ):
                    return cached

            state = cls._query_install_state(db)
            cls._cached_state = state
            cls._cache_expire_monotonic = (
                now + INSTALL_REQUIRED_CACHE_TTL_SECONDS if state.needs_install else None
            )
            return state

    @classmethod
    def refresh_state(cls, db: Session) -> InstallState:
        return cls.get_state(db, force_refresh=True)

    @classmethod
    def invalidate_cache(cls) -> None:
        with cls._cache_lock:
            cls._cached_state = None
            cls._cache_expire_monotonic = None
