"""
用户History管理控制器 - REST API路由
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user_with_key
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse
from app.schemas.user_history import (
    ImportGuestHistoryRequest,
    ImportGuestHistoryResponse,
    UserHistoryDetail,
    UserHistoryListResponse,
    UserHistorySaveRequest,
    UserHistorySearchParams,
    UserHistoryStarRequest,
)
from app.services.user_history_service import UserHistoryService

# 创建路由器
router = APIRouter(prefix="/api/user/history", tags=["用户History管理"])
logger = logging.getLogger(__name__)


@router.get("", response_model=UserHistoryListResponse)
async def get_user_history(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    starred: bool | None = Query(None, description="收藏状态过滤"),
    search: str | None = Query(None, description="搜索关键词，搜索title"),
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    获取用户的历史记录列表

    支持以下查询参数：
    - **page**: 页码
    - **limit**: 每页数量
    - **starred**: 收藏状态过滤 (true|false)
    - **search**: 搜索关键词，搜索title
    """
    current_user, _ = user_and_key

    search_params = UserHistorySearchParams(
        page=page,
        limit=limit,
        starred=starred,
        search=search,
    )

    try:
        return UserHistoryService.get_user_history(db, current_user.id, search_params)
    except Exception:
        logger.exception("获取历史记录失败 user_id=%s", current_user.id)
        raise HTTPException(
            status_code=500,
            detail="获取历史记录失败，请稍后重试",
        ) from None


@router.post("/import_guest", response_model=ImportGuestHistoryResponse)
async def import_guest_history(
    request: ImportGuestHistoryRequest,
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    导入游客历史记录并合并到用户账户

    - 允许部分成功
    - 返回 imported/skipped 统计与失败原因摘要
    - 返回导入后的最新历史快照
    """
    current_user, user_key = user_and_key

    try:
        return UserHistoryService.import_guest_history(
            db, current_user.id, user_key, request
        )
    except Exception:
        logger.exception("导入游客历史失败 user_id=%s", current_user.id)
        raise HTTPException(
            status_code=500,
            detail="导入游客历史失败，请稍后重试",
        ) from None


@router.post("/{paste_id}", response_model=UserHistoryDetail)
async def save_paste_to_history(
    paste_id: str,
    save_request: UserHistorySaveRequest,
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    将Paste保存到用户账户（upsert）

    - **encryption_key**: paste密钥，将被用户密钥加密存储
    - **admin_key**: 管理权限令牌，用于验证权限
    """
    current_user, user_key = user_and_key

    try:
        UserHistoryService.save_paste_to_history(
            db, current_user.id, paste_id, user_key, save_request
        )
        # 返回详情（含密钥）
        detail = UserHistoryService.get_user_history_detail(
            db, current_user.id, paste_id, user_key
        )
        if not detail:
            raise HTTPException(status_code=500, detail="保存后无法获取详情")
        return detail
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paste不存在",
            ) from None
        elif "权限" in str(e) or "验证失败" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="管理权限验证失败",
            ) from None
        elif "解密失败" in str(e):
            logger.exception(
                "保存历史记录后读取详情失败 user_id=%s paste_id=%s error=%s",
                current_user.id,
                paste_id,
                str(e),
            )
            raise HTTPException(
                status_code=500,
                detail="历史详情密钥解密失败，请检查数据完整性或重新保存该记录",
            ) from None
        else:
            logger.exception(
                "保存历史记录失败 user_id=%s paste_id=%s error=%s",
                current_user.id,
                paste_id,
                str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="保存历史记录失败，请检查请求参数",
            ) from None


@router.get("/{paste_id}", response_model=UserHistoryDetail)
async def get_user_history_item(
    paste_id: str,
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    获取单条历史详情（含解密后的密钥）

    用于"继续编辑/恢复访问"场景
    """
    current_user, user_key = user_and_key

    try:
        detail = UserHistoryService.get_user_history_detail(
            db, current_user.id, paste_id, user_key
        )
        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="该Paste未保存到用户账户",
            )
        return detail
    except HTTPException:
        raise
    except ValueError:
        logger.exception(
            "历史详情密钥解密失败 user_id=%s paste_id=%s",
            current_user.id,
            paste_id,
        )
        raise HTTPException(
            status_code=500,
            detail="历史详情密钥解密失败，请检查数据完整性或重新保存该记录",
        ) from None
    except Exception:
        logger.exception(
            "获取历史详情失败 user_id=%s paste_id=%s", current_user.id, paste_id
        )
        raise HTTPException(
            status_code=500,
            detail="获取历史详情失败，请稍后重试",
        ) from None


@router.put("/{paste_id}/star", response_model=MessageResponse)
async def update_history_star_status(
    paste_id: str,
    star_request: UserHistoryStarRequest,
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    收藏/取消收藏Paste

    - **is_starred**: 是否收藏
    """
    current_user, _ = user_and_key

    try:
        UserHistoryService.update_history_star_status(
            db, current_user.id, paste_id, star_request
        )
        action = "收藏" if star_request.is_starred else "取消收藏"
        return MessageResponse(message=f"已{action}该Paste")
    except ValueError as e:
        if "未保存" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="该Paste未保存到用户账户",
            ) from None
        else:
            logger.exception(
                "更新收藏状态失败 user_id=%s paste_id=%s error=%s",
                current_user.id,
                paste_id,
                str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="更新收藏状态失败，请检查请求参数",
            ) from None


@router.delete("/{paste_id}", response_model=MessageResponse)
async def remove_paste_from_history(
    paste_id: str,
    user_and_key: tuple[UserResponse, bytes] = Depends(get_current_user_with_key),
    db: Session = Depends(get_db),
):
    """
    从用户账户移除Paste（软删除）
    """
    current_user, _ = user_and_key

    try:
        UserHistoryService.soft_delete_history(db, current_user.id, paste_id)
        return MessageResponse(message="已从用户账户移除该Paste")
    except ValueError as e:
        if "未保存" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="该Paste未保存到用户账户",
            ) from None
        else:
            logger.exception(
                "移除历史记录失败 user_id=%s paste_id=%s error=%s",
                current_user.id,
                paste_id,
                str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="移除历史记录失败，请检查请求参数",
            ) from None
