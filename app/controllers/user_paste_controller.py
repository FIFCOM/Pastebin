"""
用户Paste管理控制器 - REST API路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_user_with_key
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse
from app.schemas.user_paste import (
    UserPasteInfo,
    UserPasteListResponse,
    UserPasteSaveRequest,
    UserPasteSearchParams,
    UserPasteStarRequest,
)
from app.services.user_paste_service import UserPasteService

# 创建路由器
router = APIRouter(prefix="/api/user/pastes", tags=["用户Paste管理"])


@router.get("", response_model=UserPasteListResponse)
async def get_user_pastes(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    status: str | None = Query(None, description="状态过滤：published|edited|all"),
    starred: bool | None = Query(None, description="收藏状态过滤"),
    search: str | None = Query(None, description="搜索关键词，搜索title"),
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    获取用户的所有Paste

    支持以下查询参数：
    - **page**: 页码
    - **limit**: 每页数量
    - **status**: 状态过滤 (published|edited|all)
    - **starred**: 收藏状态过滤 (true|false)
    - **search**: 搜索关键词，搜索title
    """
    current_user, user_key = user_and_key

    search_params = UserPasteSearchParams(
        page=page,
        limit=limit,
        status=status,
        starred=starred,
        search=search,
    )

    try:
        return UserPasteService.get_user_pastes(
            db, current_user.id, user_key, search_params
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取用户Paste列表失败: {str(e)}",
        ) from None


@router.post("/{paste_id}", response_model=MessageResponse)
async def save_paste_to_user(
    paste_id: str,
    save_request: UserPasteSaveRequest,
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    将Paste保存到用户账户

    - **encryption_key**: paste密钥，将被用户密钥加密存储
    - **admin_key**: 管理权限令牌，用于验证权限
    """
    current_user, user_key = user_and_key

    try:
        UserPasteService.save_paste_to_user(
            db, current_user.id, paste_id, user_key, save_request
        )
        return MessageResponse(message="Paste已成功保存到用户账户")
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        elif "权限" in str(e) or "验证失败" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "已保存" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.get("/{paste_id}", response_model=UserPasteInfo)
async def get_user_paste(
    paste_id: str,
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    获取单个用户Paste信息
    """
    current_user, user_key = user_and_key

    try:
        user_paste_info = UserPasteService.get_user_paste(
            db, current_user.id, paste_id, user_key
        )
        if not user_paste_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="该Paste未保存到用户账户",
            )
        return user_paste_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取用户Paste信息失败: {str(e)}",
        ) from None


@router.put("/{paste_id}/star", response_model=MessageResponse)
async def update_paste_star_status(
    paste_id: str,
    star_request: UserPasteStarRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    收藏/取消收藏Paste

    - **is_starred**: 是否收藏
    """
    try:
        UserPasteService.update_paste_star_status(
            db, current_user.id, paste_id, star_request
        )
        action = "收藏" if star_request.is_starred else "取消收藏"
        return MessageResponse(message=f"已{action}该Paste")
    except ValueError as e:
        if "未保存" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.delete("/{paste_id}", response_model=MessageResponse)
async def remove_paste_from_user(
    paste_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    从用户账户移除Paste
    """
    try:
        UserPasteService.remove_paste_from_user(db, current_user.id, paste_id)
        return MessageResponse(message="已从用户账户移除该Paste")
    except ValueError as e:
        if "未保存" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None
