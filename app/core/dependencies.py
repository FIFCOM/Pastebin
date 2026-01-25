"""
依赖注入函数
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    decrypt_session_key,
    decrypt_with_key,
    str_to_bytes,
    verify_token,
)
from app.core.time_utils import is_expired
from app.models.user import UserSession, UserSessionKey
from app.schemas.user import UserResponse
from app.services.api_key_service import ApiKeyService
from app.services.user_service import UserService

# HTTP Bearer 安全方案
# - required: 缺少/无效 Authorization 直接报错
# - optional: 缺少 Authorization 返回 None（用于“可匿名”接口）
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    获取当前用户

    支持两种认证方式：
    1. Session Token (JWT)
    2. API Key (以 pk_ 开头)

    Args:
        credentials: HTTP Bearer 凭据
        db: 数据库会话

    Returns:
        当前用户信息

    Raises:
        HTTPException: 当token无效或用户不存在时
    """
    token = credentials.credentials

    # 检查是否为API Key（以pk_开头）
    if token.startswith("pk_"):
        user = ApiKeyService.authenticate_api_key(db, token)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的API密钥",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    # 否则作为Session Token处理
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str | None = payload.get("sub")
    session_id: str | None = payload.get("session_id")
    token_type: str | None = payload.get("type")

    if username is None or session_id is None or token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 获取用户
    user = UserService.get_user_by_username(db, username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 校验会话有效性（支持主动登出/单设备登出/风控撤销等）
    session = (
        db.query(UserSession)
        .filter(UserSession.id == session_id, UserSession.user_id == user.id)
        .first()
    )
    if session is None or is_expired(session.expires_at):  # type: ignore[arg-type]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话不存在或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> UserResponse | None:
    """
    获取可选的当前用户（可以为空）

    支持两种认证方式：
    1. Session Token (JWT)
    2. API Key (以 pk_ 开头)

    Args:
        credentials: HTTP Bearer 凭据（可选）
        db: 数据库会话

    Returns:
        当前用户信息或None
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_current_user_with_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> tuple[UserResponse, bytes]:
    """
    获取当前用户及其解密密钥

    Args:
        credentials: HTTP Bearer 凭据
        db: 数据库会话

    Returns:
        (用户信息, 用户密钥)

    Raises:
        HTTPException: 当token无效、用户不存在或无法恢复密钥时
    """
    token = credentials.credentials

    # API Key认证暂不支持密钥恢复
    if token.startswith("pk_"):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="API Key认证暂不支持用户Paste管理功能，请使用Session Token认证",
        )

    # Session Token处理
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 获取用户名和会话ID
    username: str | None = payload.get("sub")
    session_id: str | None = payload.get("session_id")
    token_type: str | None = payload.get("type")

    if username is None or session_id is None or token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据，缺少必要信息",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 获取用户信息
    user = UserService.get_user_by_username(db, username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 获取会话信息
    session = (
        db.query(UserSession)
        .filter(UserSession.id == session_id, UserSession.user_id == user.id)
        .first()
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话不存在或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查会话是否过期（兼容 SQLite 返回的 naive datetime）
    if is_expired(session.expires_at):  # type: ignore[arg-type]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_key_record = (
        db.query(UserSessionKey).filter(UserSessionKey.session_id == session_id).first()
    )
    if session_key_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话密钥不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 恢复用户密钥
    try:
        session_key_bytes = decrypt_session_key(
            str(session_key_record.encrypted_session_key), session_id
        )
        encrypted_user_key_bytes = str_to_bytes(str(session.encrypted_session_key))  # type: ignore
        user_key = decrypt_with_key(encrypted_user_key_bytes, session_key_bytes)
        return user, user_key
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"用户密钥恢复失败: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
