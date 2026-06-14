"""
用户控制器 - REST API路由
"""

from typing import Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user_and_session,
    get_current_user_by_access_token,
)
from app.core.request_meta import extract_client_ip, extract_user_agent
from app.schemas.common import MessageResponse
from app.schemas.user import (
    ChangeEmailVerificationCodeRequest,
    EmailVerificationCodeRequest,
    LoginResponse,
    PasswordResetRequest,
    RefreshTokenResponse,
    SessionResponse,
    TotpSetupResponse,
    TotpStatusResponse,
    TotpVerifyRequest,
    UserCreateRequest,
    UserListResponse,
    UserLoginRequest,
    UserLoginWithTotpRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.email_verification_service import EmailVerificationService
from app.services.user_service import UserService
from config.config import settings

REFRESH_TOKEN_COOKIE_NAME = "mb_refresh_token"


def _set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    max_age = settings.refresh_token_expire_days * 24 * 60 * 60
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=max_age,
        path="/api/users",
    )


def _clear_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE_NAME, path="/api/users")


def _is_admin(user: UserResponse) -> bool:
    return user.role == "admin"


def _require_admin(user: UserResponse) -> None:
    if not _is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可执行该操作"
        )


def _map_user_service_error(error: ValueError) -> HTTPException:
    message = str(error)
    if "无权限" in message:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
    if "不存在" in message:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


# 创建路由器
router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(user_data: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    用户注册

    - **email**: 用户邮箱
    - **password**: SHA256哈希后的密码
    """
    try:
        return UserService.register_user(db, user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.post("/email-verification-codes", response_model=MessageResponse)
async def send_email_verification_code(
    payload: EmailVerificationCodeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    发送公开邮箱验证码。

    - **purpose=register**: 注册验证码
    - **purpose=reset_password**: 找回密码验证码
    """
    try:
        dispatch = EmailVerificationService.send_public_code(
            db,
            email=str(payload.email),
            purpose=payload.purpose,
            ip_address=extract_client_ip(request),
        )
        if dispatch is not None:
            background_tasks.add_task(
                EmailVerificationService.send_prepared_code,
                dispatch.record_id,
                dispatch.code,
            )
        return MessageResponse(message="如邮箱可用，验证码已发送")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.post("/me/email-verification-code", response_model=MessageResponse)
async def send_change_email_verification_code(
    payload: ChangeEmailVerificationCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
):
    """发送修改邮箱验证码。"""
    try:
        EmailVerificationService.send_change_email_code(
            db,
            email=str(payload.email),
            user_id=current_user.id,
            ip_address=extract_client_ip(request),
        )
        return MessageResponse(message="验证码已发送")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.post("/password-reset", response_model=MessageResponse)
async def reset_password(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """通过邮箱验证码重置密码。"""
    try:
        UserService.reset_password(db, payload)
        return MessageResponse(
            message="密码已重置，历史记录和收藏关联已清空，请使用新密码登录"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.post("/login", response_model=LoginResponse)
async def login_user(
    login_data: UserLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    用户登录

    - **email**: 用户邮箱
    - **password**: SHA256哈希后的密码
    """
    try:
        login_response, refresh_token = UserService.login_user(
            db,
            login_data,
            user_agent=extract_user_agent(request),
            ip_address=extract_client_ip(request),
        )
        _set_refresh_token_cookie(response, refresh_token)
        return login_response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


@router.post("/login-totp", response_model=LoginResponse)
async def login_user_with_totp(
    login_data: UserLoginWithTotpRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    用户TOTP登录

    - **email**: 用户邮箱
    - **password**: SHA256哈希后的密码
    - **totp_code**: 6位TOTP验证码
    """
    try:
        login_response, refresh_token = UserService.login_user_with_totp(
            db,
            login_data,
            user_agent=extract_user_agent(request),
            ip_address=extract_client_ip(request),
        )
        _set_refresh_token_cookie(response, refresh_token)
        return login_response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(None, alias=REFRESH_TOKEN_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    """
    使用 refresh token 续期 access token（并旋转 refresh token）

    - 仅使用 HttpOnly Cookie: mb_refresh_token
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 refresh token"
        )

    try:
        access_token, new_refresh_token = UserService.refresh_access_token(
            db,
            refresh_token,
            user_agent=extract_user_agent(request),
            ip_address=extract_client_ip(request),
        )
        _set_refresh_token_cookie(response, new_refresh_token)
        return RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
        )
    except ValueError as e:
        _clear_refresh_token_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from None


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(None, alias=REFRESH_TOKEN_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    """
    主动登出（撤销当前会话 refresh token）

    - 仅使用 HttpOnly Cookie: mb_refresh_token
    """
    if refresh_token:
        UserService.logout_by_refresh_token(db, refresh_token)
    _clear_refresh_token_cookie(response)
    return MessageResponse(message="已登出")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    response: Response,
    current_user: UserResponse = Depends(get_current_user_by_access_token),
    db: Session = Depends(get_db),
):
    """全部设备登出（撤销用户所有会话）"""
    count = UserService.logout_all_sessions(db, current_user.id)
    _clear_refresh_token_cookie(response)
    return MessageResponse(message=f"已撤销 {count} 个会话")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user_by_access_token),
):
    """获取当前用户信息"""
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
):
    """根据ID获取用户信息"""
    if not _is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权限查看其他用户"
        )

    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
):
    """
    更新用户信息

    - 普通用户：仅可更新自己用户名/邮箱/密码；修改邮箱或密码时必须提供 current_password
    - 管理员：可更新任意用户的用户名/邮箱/密码/角色/状态
    """
    try:
        return UserService.update_user(
            db,
            user_id,
            user_data,
            actor_user_id=current_user.id,
            actor_is_admin=_is_admin(current_user),
        )
    except ValueError as e:
        raise _map_user_service_error(e) from None


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
):
    """
    删除用户

    - 普通用户：仅可删除自己的账户
    - 管理员：可删除任意用户
    """
    try:
        success = UserService.delete_user(
            db,
            user_id,
            actor_user_id=current_user.id,
            actor_is_admin=_is_admin(current_user),
        )
    except ValueError as e:
        raise _map_user_service_error(e) from None

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return MessageResponse(message="用户已删除")


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页大小"),
    search: str | None = Query(None, description="按用户名/邮箱搜索"),
    role: Literal["admin", "user"] | None = Query(None, description="角色筛选"),
    is_active: bool | None = Query(None, description="状态筛选"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
):
    """获取用户列表（管理员）"""
    _require_admin(current_user)
    return UserService.list_users(
        db,
        page,
        size,
        search=search,
        role=role,
        is_active=is_active,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
):
    """
    创建用户（管理员）

    - **username**: 用户名（可选，留空自动生成）
    - **email**: 用户邮箱
    - **password**: SHA256哈希后的密码
    - **role**: 用户角色（admin/user）
    """
    _require_admin(current_user)

    try:
        return UserService.create_user(db, user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.get("/{user_id}/sessions", response_model=list[SessionResponse])
async def get_user_sessions(
    user_id: int,
    db: Session = Depends(get_db),
    current: tuple[UserResponse, str] = Depends(get_current_user_and_session),
):
    """
    获取用户会话列表

    仅支持用户查看自己的会话。
    """
    current_user, current_session_id = current
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权限查看其他用户的会话"
        )

    return UserService.get_user_sessions(
        db, user_id, current_session_id=current_session_id
    )


@router.delete("/{user_id}/sessions/others", response_model=MessageResponse)
async def revoke_other_sessions(
    user_id: int,
    db: Session = Depends(get_db),
    current: tuple[UserResponse, str] = Depends(get_current_user_and_session),
):
    """撤销当前用户的其他设备会话（保留当前会话）。"""
    current_user, current_session_id = current
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权限操作其他用户的会话"
        )

    count = UserService.revoke_other_sessions(db, user_id, current_session_id)
    return MessageResponse(message=f"已撤销 {count} 个其他会话")


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
):
    """
    撤销会话

    用户只能撤销自己的会话
    """
    success = UserService.revoke_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在或无权限"
        )

    return MessageResponse(message="会话已撤销")


@router.post("/cleanup-sessions", response_model=MessageResponse)
async def cleanup_expired_sessions(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
):
    """清理过期会话（管理员）"""
    _require_admin(current_user)

    sessions_count = UserService.cleanup_expired_sessions(db)
    used_tokens_count = UserService.cleanup_expired_used_refresh_tokens(db)
    return MessageResponse(
        message=f"已清理 {sessions_count} 个过期会话，{used_tokens_count} 条 refresh token 记录"
    )


@router.get("/me/totp", response_model=TotpStatusResponse)
async def get_totp_status(
    current_user: UserResponse = Depends(get_current_user_by_access_token),
    db: Session = Depends(get_db),
):
    """
    获取当前用户的TOTP状态
    """
    try:
        return UserService.get_totp_status(db, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None


@router.post("/me/totp", response_model=TotpSetupResponse)
async def setup_totp(
    current_user: UserResponse = Depends(get_current_user_by_access_token),
    db: Session = Depends(get_db),
):
    """
    设置TOTP两步验证

    返回 TOTP 密钥与 provisioning URI（前端生成二维码展示），用户扫码后调用 verify 接口验证启用
    """
    try:
        return UserService.setup_totp(db, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.post("/me/totp/verify", response_model=MessageResponse)
async def verify_totp(
    totp_data: TotpVerifyRequest,
    current_user: UserResponse = Depends(get_current_user_by_access_token),
    db: Session = Depends(get_db),
):
    """
    验证并启用TOTP

    - **totp_code**: 6位TOTP验证码
    """
    try:
        success = UserService.verify_and_enable_totp(db, current_user.id, totp_data)
        if success:
            return MessageResponse(message="TOTP验证成功，两步验证已启用")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP验证码错误"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.delete("/me/totp", response_model=MessageResponse)
async def disable_totp(
    current_user: UserResponse = Depends(get_current_user_by_access_token),
    db: Session = Depends(get_db),
):
    """
    禁用TOTP两步验证
    """
    try:
        success = UserService.disable_totp(db, current_user.id)
        if success:
            return MessageResponse(message="TOTP两步验证已禁用")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="禁用TOTP失败"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None
