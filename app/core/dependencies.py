"""
依赖注入函数
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.request_meta import extract_client_ip, extract_user_agent
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


def _auth_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _resolve_access_session(token: str, db: Session) -> tuple[UserResponse, str]:
    payload = verify_token(token)
    if payload is None:
        raise _auth_error("无效的认证凭据")

    uid_claim = payload.get("uid")
    session_id: str | None = payload.get("session_id")
    token_type: str | None = payload.get("type")

    if session_id is None or token_type != "access":
        raise _auth_error("无效的认证凭据")

    if type(uid_claim) is int:
        user_id = uid_claim
    elif isinstance(uid_claim, str):
        uid_text = uid_claim.strip()
        if not uid_text:
            raise _auth_error("无效的认证凭据")
        try:
            user_id = int(uid_text)
        except ValueError as e:
            raise _auth_error("无效的认证凭据") from e
    else:
        raise _auth_error("无效的认证凭据")

    if user_id <= 0:
        raise _auth_error("无效的认证凭据")

    user = UserService.get_user_by_id(db, user_id)
    if user is None:
        raise _auth_error("用户不存在")
    if not user.is_active:
        raise _auth_error("账户已被禁用")

    session = (
        db.query(UserSession)
        .filter(UserSession.id == session_id, UserSession.user_id == user.id)
        .first()
    )
    if session is None or is_expired(session.expires_at):  # type: ignore[arg-type]
        raise _auth_error("会话不存在或已过期")

    return user, session_id


def _require_access_token(token: str) -> None:
    if token.startswith("pk_"):
        raise _auth_error("当前接口仅支持 access_token 认证")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    获取当前用户

    支持两种认证方式：
    1. Session Token (JWT)
    2. API Key (以 pk_ 开头)
    """
    token = credentials.credentials
    ip_address = extract_client_ip(request)

    if token.startswith("pk_"):
        user = ApiKeyService.authenticate_api_key(db, token, ip_address=ip_address)
        if user is None:
            raise _auth_error("无效的API密钥")
        return user

    user, session_id = _resolve_access_session(token, db)
    UserService.touch_session_activity(
        db,
        session_id,
        ip_address=ip_address,
        user_agent=extract_user_agent(request),
    )
    return user


async def get_current_user_by_access_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserResponse:
    """仅允许通过 access_token 获取当前用户。"""
    token = credentials.credentials
    _require_access_token(token)

    user, session_id = _resolve_access_session(token, db)
    UserService.touch_session_activity(
        db,
        session_id,
        ip_address=extract_client_ip(request),
        user_agent=extract_user_agent(request),
    )
    return user


async def get_current_user_and_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> tuple[UserResponse, str]:
    """获取当前用户以及当前 access token 对应的 session_id。"""
    token = credentials.credentials
    _require_access_token(token)

    user, session_id = _resolve_access_session(token, db)
    UserService.touch_session_activity(
        db,
        session_id,
        ip_address=extract_client_ip(request),
        user_agent=extract_user_agent(request),
    )
    return user, session_id


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> UserResponse | None:
    """
    获取可选的当前用户（可以为空）
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None


async def get_current_user_with_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> tuple[UserResponse, bytes]:
    """
    获取当前用户及其解密密钥

    Returns:
        (用户信息, 用户密钥)
    """
    token = credentials.credentials

    if token.startswith("pk_"):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="API Key认证暂不支持用户Paste管理功能，请使用Session Token认证",
        )

    user, session_id = _resolve_access_session(token, db)

    session = (
        db.query(UserSession)
        .filter(UserSession.id == session_id, UserSession.user_id == user.id)
        .first()
    )
    if session is None:
        raise _auth_error("会话不存在或已过期")

    session_key_record = (
        db.query(UserSessionKey).filter(UserSessionKey.session_id == session_id).first()
    )
    if session_key_record is None:
        raise _auth_error("会话密钥不存在")

    UserService.touch_session_activity(
        db,
        session_id,
        ip_address=extract_client_ip(request),
        user_agent=extract_user_agent(request),
    )

    try:
        session_key_bytes = decrypt_session_key(
            str(session_key_record.encrypted_session_key), session_id
        )
        encrypted_user_key_bytes = str_to_bytes(str(session.encrypted_session_key))  # type: ignore[arg-type]
        user_key = decrypt_with_key(encrypted_user_key_bytes, session_key_bytes)
        return user, user_key
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"用户密钥恢复失败: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
