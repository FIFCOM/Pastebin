"""
用户控制器 - REST API路由
"""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.common import MessageResponse
from app.schemas.user import (
    LoginResponse,
    RefreshTokenRequest,
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
        user = UserService.register_user(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.post("/login", response_model=LoginResponse)
async def login_user(
    login_data: UserLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    用户登录

    - **email**: 用户邮箱
    - **password**: SHA256哈希后的密码
    """
    try:
        login_response = UserService.login_user(db, login_data)
        _set_refresh_token_cookie(response, login_response.refresh_token)
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
        login_response = UserService.login_user_with_totp(db, login_data)
        _set_refresh_token_cookie(response, login_response.refresh_token)
        return login_response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(
    response: Response,
    refresh_token: str | None = Cookie(None, alias=REFRESH_TOKEN_COOKIE_NAME),
    refresh_data: RefreshTokenRequest | None = None,
    db: Session = Depends(get_db),
):
    """
    使用 refresh token 续期 access token（并旋转 refresh token）

    - 优先使用 HttpOnly Cookie: mb_refresh_token
    - 若 Cookie 不存在，可在 JSON body 提供 refresh_token（适用于移动端等非浏览器场景）
    """
    token = refresh_token or (refresh_data.refresh_token if refresh_data else None)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 refresh token"
        )

    try:
        access_token, new_refresh_token = UserService.refresh_access_token(db, token)
        _set_refresh_token_cookie(response, new_refresh_token)
        return RefreshTokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
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
    refresh_data: RefreshTokenRequest | None = None,
    db: Session = Depends(get_db),
):
    """
    主动登出（撤销当前会话 refresh token）

    - 优先使用 HttpOnly Cookie: mb_refresh_token
    - 若 Cookie 不存在，可在 JSON body 提供 refresh_token
    """
    token = refresh_token or (refresh_data.refresh_token if refresh_data else None)
    if token:
        UserService.logout_by_refresh_token(db, token)
    _clear_refresh_token_cookie(response)
    return MessageResponse(message="已登出")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """全部设备登出（撤销用户所有会话）"""
    count = UserService.logout_all_sessions(db, current_user.id)
    _clear_refresh_token_cookie(response)
    return MessageResponse(message=f"已撤销 {count} 个会话")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """根据ID获取用户信息"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    更新用户信息

    用户只能更新自己的信息
    """
    # 检查权限：用户只能更新自己的信息
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权限修改其他用户信息"
        )

    try:
        updated_user = UserService.update_user(db, user_id, user_data)
        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    删除用户

    用户只能删除自己的账户
    """
    # 检查权限：用户只能删除自己的账户
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权限删除其他用户"
        )

    success = UserService.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return MessageResponse(message="用户已删除")


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页大小"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    获取用户列表（分页）

    需要登录
    """
    return UserService.list_users(db, page, size)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    创建用户（管理功能）

    - **username**: 用户名（可选，留空自动生成）
    - **email**: 用户邮箱
    - **password**: SHA256哈希后的密码
    """
    try:
        user = UserService.create_user(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.get("/{user_id}/sessions", response_model=list[SessionResponse])
async def get_user_sessions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    获取用户的所有会话

    用户只能查看自己的会话
    """
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权限查看其他用户的会话"
        )

    return UserService.get_user_sessions(db, user_id)


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
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
    current_user: UserResponse = Depends(get_current_user),
):
    """清理过期会话（管理功能）"""
    sessions_count = UserService.cleanup_expired_sessions(db)
    used_tokens_count = UserService.cleanup_expired_used_refresh_tokens(db)
    return MessageResponse(
        message=f"已清理 {sessions_count} 个过期会话，{used_tokens_count} 条 refresh token 记录"
    )


@router.get("/me/totp", response_model=TotpStatusResponse)
async def get_totp_status(
    current_user: UserResponse = Depends(get_current_user),
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
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    设置TOTP两步验证

    返回TOTP密钥和二维码，用户需要用验证器应用扫描后调用verify接口验证启用
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
    current_user: UserResponse = Depends(get_current_user),
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
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP验证码错误"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.delete("/me/totp", response_model=MessageResponse)
async def disable_totp(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    禁用TOTP两步验证
    """
    try:
        success = UserService.disable_totp(db, current_user.id)
        if success:
            return MessageResponse(message="TOTP两步验证已禁用")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="禁用TOTP失败"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None
