"""
数据库初始化
"""

import app.models  # noqa: F401
from app.core.database import Base, SessionLocal, engine
from app.services.runtime_settings_service import RuntimeSettingsService
from config.config import settings


def create_tables():
    """创建所有数据库表"""
    print("正在创建数据库表...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        RuntimeSettingsService.ensure_defaults(db)
    finally:
        db.close()
    print("数据库表创建完成")


def drop_tables():
    """删除所有数据库表"""
    print("正在删除数据库表...")
    Base.metadata.drop_all(bind=engine)
    print("数据库表删除完成")


def reset_database():
    """重置数据库（删除后重新创建）"""
    print("正在重置数据库...")
    drop_tables()
    create_tables()
    print("数据库重置完成")


def init_database():
    """初始化数据库"""
    print(f"使用数据库: {settings.database_url}")
    create_tables()


if __name__ == "__main__":
    init_database()
