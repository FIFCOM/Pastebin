"""
数据库配置和连接
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config.config import settings

# 根据数据库URL选择合适的引擎配置
if settings.database_url.startswith("sqlite"):
    # SQLite配置
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=settings.debug,
    )
elif settings.mysql_database_url and settings.mysql_database_url.startswith("mysql"):
    # MySQL配置
    engine = create_engine(settings.mysql_database_url, echo=settings.debug)
else:
    # 默认使用SQLite
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=settings.debug,
    )

def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """确保SQLite连接启用外键约束"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


if engine.url.get_backend_name() == "sqlite":
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明式基类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
