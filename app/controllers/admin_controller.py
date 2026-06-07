"""
管理员后台控制器
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user_by_access_token
from app.schemas.admin import (
    AdminCleanupStatusResponse,
    AdminOverviewResponse,
    AdminPasteListResponse,
)
from app.schemas.cleanup import CleanupRequest, CleanupResponse
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse
from app.services.admin_service import SUPPORTED_CLEANUP_TASKS, AdminService
from app.services.cleanup_service import CleanupService

router = APIRouter(prefix="/api/users/admin", tags=["管理员后台"])


def _require_admin(user: UserResponse) -> None:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可执行该操作"
        )


@router.get("/overview", response_model=AdminOverviewResponse)
async def get_admin_overview(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
) -> AdminOverviewResponse:
    """获取管理员概览统计。"""
    _require_admin(current_user)
    return AdminService.get_overview(db)


@router.get("/pastes", response_model=AdminPasteListResponse)
async def list_admin_pastes(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页大小"),
    search: str | None = Query(None, description="按 Paste ID 或标题搜索"),
    status_filter: Literal["draft", "published", "edited"] | None = Query(
        None, alias="status", description="状态筛选"
    ),
    paste_type: Literal["txt", "md"] | None = Query(
        None, alias="type", description="类型筛选"
    ),
    encryption_mode: Literal["client", "server"] | None = Query(
        None, description="加密模式筛选"
    ),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
) -> AdminPasteListResponse:
    """获取 Paste 元数据列表。"""
    _require_admin(current_user)
    return AdminService.list_pastes(
        db,
        page,
        size,
        search=search,
        status=status_filter,
        paste_type=paste_type,
        encryption_mode=encryption_mode,
    )


@router.delete("/pastes/{paste_id}", response_model=MessageResponse)
async def delete_admin_paste(
    paste_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
) -> MessageResponse:
    """删除 Paste 及其关联物理文件。"""
    _require_admin(current_user)
    try:
        success = AdminService.delete_paste(db, paste_id)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除 Paste 失败: {str(e)}",
        ) from e

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paste不存在")

    return MessageResponse(message="Paste已删除")


@router.get("/cleanup", response_model=AdminCleanupStatusResponse)
async def get_admin_cleanup_status(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
) -> AdminCleanupStatusResponse:
    """获取管理员清理任务状态。"""
    _require_admin(current_user)
    return AdminService.get_cleanup_status(db)


@router.post("/cleanup", response_model=CleanupResponse)
async def execute_admin_cleanup(
    cleanup_request: CleanupRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_by_access_token),
) -> CleanupResponse:
    """执行管理员清理任务。"""
    _require_admin(current_user)

    invalid_tasks = set(cleanup_request.tasks) - set(SUPPORTED_CLEANUP_TASKS)
    if invalid_tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的清理任务: {', '.join(sorted(invalid_tasks))}",
        )

    return await CleanupService.execute_cleanup_tasks_async(db, cleanup_request.tasks)
