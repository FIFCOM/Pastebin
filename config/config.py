"""
配置加载器
"""

import os
from dataclasses import dataclass

# Optional: load .env if present
try:
    from dotenv import load_dotenv  # type: ignore

    _HAS_DOTENV = True
except Exception:
    # If import fails, define a no-op to satisfy type checkers
    def load_dotenv(*args, **kwargs):  # type: ignore
        return None

    _HAS_DOTENV = False


def load_env_file() -> None:
    """
    Load .env from project root if present.
    Safe to call multiple times; noop if python-dotenv not installed.
    """
    if _HAS_DOTENV:
        # load from current working directory (project root in typical runs)
        load_dotenv(override=False)


def _bool_env(name: str, default: bool = False) -> bool:
    """解析环境变量中的布尔值"""
    v = os.getenv(name)
    if v is None or v == "":
        return default
    v_lower = v.strip().lower()
    return v_lower in ("1", "true", "yes", "y", "on")


def _int_env(name: str, default: int) -> int:
    """解析环境变量中的整数值"""
    v = os.getenv(name)
    if v is None or v == "":
        return default
    try:
        return int(v.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """应用配置"""

    # 应用设置
    app_name: str
    version: str
    debug: bool

    # 数据库设置
    database_url: str

    # 安全设置
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    member_token_secret_key: str

    # 加密设置
    pbkdf2_iterations: int
    salt_length: int
    encryption_key_length: int
    session_key_length: int

    # 服务器配置
    host: str
    port: int

    # 数据存储配置
    data_dir: str

    # 内部服务配置
    internal_token: str


def load_config() -> Settings:
    """
    从环境变量加载应用配置。
    优先顺序：
    - .env（若安装了 python-dotenv）
    - 系统环境变量
    - 默认值
    """
    load_env_file()

    secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    return Settings(
        # 应用设置
        app_name=os.getenv("APP_NAME", "Material Bin User Auth API"),
        version=os.getenv("VERSION", "1.0.8"),
        debug=_bool_env("DEBUG", True),
        # 数据库设置
        database_url=os.getenv("DATABASE_URL", "sqlite:///./material_bin.db"),
        # 安全设置
        secret_key=secret_key,
        algorithm=os.getenv("ALGORITHM", "HS256"),
        access_token_expire_minutes=_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 30),
        refresh_token_expire_days=_int_env("REFRESH_TOKEN_EXPIRE_DAYS", 30),
        # 协作房间 member token（必须显式设置，且建议与 SECRET_KEY 分离）
        member_token_secret_key=os.getenv(
            "MEMBER_TOKEN_SECRET_KEY",
            "change-this-member-token-secret-key-in-production",
        ),
        # 加密设置
        pbkdf2_iterations=_int_env("PBKDF2_ITERATIONS", 100000),
        salt_length=_int_env("SALT_LENGTH", 32),
        encryption_key_length=_int_env("ENCRYPTION_KEY_LENGTH", 16),
        session_key_length=_int_env("SESSION_KEY_LENGTH", 32),
        # 服务器配置
        host=os.getenv("HOST", "0.0.0.0"),
        port=_int_env("PORT", 8000),
        # 数据存储配置
        data_dir=os.getenv("DATA_DIR", "./data"),
        # 内部服务配置
        internal_token=os.getenv(
            "INTERNAL_TOKEN", "change-this-internal-token-in-production"
        ),
    )


def validate_config(config: Settings) -> None:
    """验证配置的完整性"""
    missing = []

    # 检查关键配置
    if config.secret_key == "your-secret-key-change-this-in-production":
        missing.append("SECRET_KEY (using default, change for production)")

    if not config.database_url:
        missing.append("DATABASE_URL")

    if config.internal_token == "change-this-internal-token-in-production":
        missing.append("INTERNAL_TOKEN (using default, change for production)")

    if config.member_token_secret_key == "change-this-member-token-secret-key-in-production":
        missing.append(
            "MEMBER_TOKEN_SECRET_KEY (using default, change for production)"
        )

    if missing:
        raise RuntimeError(
            f"Configuration issues: {', '.join(missing)}. "
            "Please set them in environment variables or a .env file."
        )


# 全局配置实例
settings = load_config()
