"""
用户收藏Paste控制器 - REST API路由
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user_with_key
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse
from app.schemas.user_favorite import (
    ImportGuestFavoritesRequest,
    ImportGuestFavoritesResponse,
    UserFavoriteDetail,
    UserFavoriteListResponse,
    UserFavoriteSaveRequest,
    UserFavoriteSearchParams,
)
from app.services.user_favorite_service import UserFavoriteService

router = APIRouter(prefix="/api/user/favorites", tags=["用户收藏管理"])
logger = logging.getLogger(__name__)


@router.get("", response_model=UserFavoriteListResponse)
async def get_user_favorites(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, description="搜索关键词，搜索title"),
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    获取用户收藏列表。

    列表响应不包含明文 encryption_key。
    """
    current_user, _ = user_and_key
    search_params = UserFavoriteSearchParams(
        page=page,
        limit=limit,
        search=search,
    )

    try:
        return UserFavoriteService.get_user_favorites(
            db, current_user.id, search_params
        )
    except Exception:
        logger.exception("获取收藏列表失败 user_id=%s", current_user.id)
        raise HTTPException(
            status_code=500,
            detail="获取收藏列表失败，请稍后重试",
        ) from None


@router.post("/import_guest", response_model=ImportGuestFavoritesResponse)
async def import_guest_favorites(
    request: ImportGuestFavoritesRequest,
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    导入游客收藏并合并到用户账户。

    - 允许部分成功
    - 返回 imported/skipped 统计与失败原因摘要
    - 返回导入后的最新收藏快照
    """
    current_user, user_key = user_and_key

    try:
        return UserFavoriteService.import_guest_favorites(
            db, current_user.id, user_key, request
        )
    except Exception:
        logger.exception("导入游客收藏失败 user_id=%s", current_user.id)
        raise HTTPException(
            status_code=500,
            detail="导入游客收藏失败，请稍后重试",
        ) from None


@router.put("/{paste_id}", response_model=UserFavoriteDetail)
async def save_user_favorite(
    paste_id: str,
    save_request: UserFavoriteSaveRequest,
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    保存Paste收藏（upsert）。

    仅保存 Paste 解密密钥；access_key 只用于本次授权校验，不保存。
    """
    current_user, user_key = user_and_key

    try:
        UserFavoriteService.save_favorite(
            db, current_user.id, paste_id, user_key, save_request
        )
        detail = UserFavoriteService.get_user_favorite_detail(
            db, current_user.id, paste_id, user_key
        )
        if not detail:
            raise HTTPException(status_code=500, detail="保存后无法获取详情")
        return detail
    except HTTPException:
        raise
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paste不存在",
            ) from None
        if "草稿状态" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paste不存在或不可访问",
            ) from None
        if "访问密钥" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="访问密钥错误",
            ) from None
        if "过期" in str(e):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Paste已过期",
            ) from None
        if "最大查看次数" in str(e):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Paste已达到最大查看次数",
            ) from None
        if "解密失败" in str(e):
            logger.exception(
                "保存收藏后读取详情失败 user_id=%s paste_id=%s error=%s",
                current_user.id,
                paste_id,
                str(e),
            )
            raise HTTPException(
                status_code=500,
                detail="收藏详情密钥解密失败，请检查数据完整性或重新保存该记录",
            ) from None
        logger.exception(
            "保存收藏失败 user_id=%s paste_id=%s error=%s",
            current_user.id,
            paste_id,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="保存收藏失败，请检查请求参数",
        ) from None


@router.get("/{paste_id}", response_model=UserFavoriteDetail)
async def get_user_favorite_item(
    paste_id: str,
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    获取单条收藏详情（含解密后的 encryption_key）。
    """
    current_user, user_key = user_and_key

    try:
        detail = UserFavoriteService.get_user_favorite_detail(
            db, current_user.id, paste_id, user_key
        )
        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="该Paste未收藏",
            )
        return detail
    except HTTPException:
        raise
    except ValueError:
        logger.exception(
            "收藏详情密钥解密失败 user_id=%s paste_id=%s",
            current_user.id,
            paste_id,
        )
        raise HTTPException(
            status_code=500,
            detail="收藏详情密钥解密失败，请检查数据完整性或重新保存该记录",
        ) from None
    except Exception:
        logger.exception(
            "获取收藏详情失败 user_id=%s paste_id=%s", current_user.id, paste_id
        )
        raise HTTPException(
            status_code=500,
            detail="获取收藏详情失败，请稍后重试",
        ) from None


@router.delete("/{paste_id}", response_model=MessageResponse)
async def remove_user_favorite(
    paste_id: str,
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """取消收藏Paste（软删除）。"""
    current_user, _ = user_and_key

    try:
        UserFavoriteService.soft_delete_favorite(db, current_user.id, paste_id)
        return MessageResponse(message="已取消收藏该Paste")
    except ValueError as e:
        if "未收藏" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="该Paste未收藏",
            ) from None
        logger.exception(
            "取消收藏失败 user_id=%s paste_id=%s error=%s",
            current_user.id,
            paste_id,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="取消收藏失败，请检查请求参数",
        ) from None
