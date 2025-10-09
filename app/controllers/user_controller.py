"""
用户控制器 - REST API路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.common import MessageResponse
from app.schemas.user import (
    LoginResponse,
    SessionResponse,
    UserCreateRequest,
    UserListResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.user_service import UserService

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
async def login_user(login_data: UserLoginRequest, db: Session = Depends(get_db)):
    """
    用户登录

    - **username**: 用户名
    - **password**: SHA256哈希后的密码
    """
    try:
        login_response = UserService.login_user(db, login_data)
        return login_response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


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
    count = UserService.cleanup_expired_sessions(db)
    return MessageResponse(message=f"已清理 {count} 个过期会话")
