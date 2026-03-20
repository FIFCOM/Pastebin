"""
清理任务控制器
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.cleanup import CleanupRequest, CleanupResponse
from app.services.cleanup_service import CleanupService
from config.config import settings

# 创建路由器
router = APIRouter(prefix="/api/internal", tags=["内部任务"])


def verify_internal_token(authorization: str = Header(...)) -> None:
    """
    验证内部认证令牌

    Args:
        authorization: Authorization header

    Raises:
        HTTPException: 当令牌无效时
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的Authorization格式")

    token = authorization[7:]  # 移除 "Bearer " 前缀

    # 从配置获取内部令牌
    if token != settings.internal_token:
        raise HTTPException(status_code=401, detail="无效的内部认证令牌")


@router.post("/cleanup", response_model=CleanupResponse)
async def execute_cleanup_tasks(
    cleanup_request: CleanupRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_token),
) -> CleanupResponse:
    """
    执行清理任务

    Args:
        cleanup_request: 清理任务请求
        db: 数据库会话
        _: 内部认证验证

    Returns:
        清理任务执行结果

    Raises:
        HTTPException: 当任务执行失败时
    """
    try:
        # 验证任务类型
        valid_tasks = {
            "expired_drafts",
            "expired_pastes",
            "expired_members",
            "expired_uploads",
            "expired_user_sessions",
            "expired_used_refresh_tokens",
        }
        invalid_tasks = set(cleanup_request.tasks) - valid_tasks

        if invalid_tasks:
            raise HTTPException(
                status_code=400, detail=f"不支持的清理任务: {', '.join(invalid_tasks)}"
            )

        # 执行清理任务
        result = await CleanupService.execute_cleanup_tasks_async(
            db, cleanup_request.tasks
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"清理任务执行失败: {str(e)}"
        ) from e


@router.get("/cleanup/status")
async def get_cleanup_status(
    _: None = Depends(verify_internal_token),
) -> dict[str, object]:
    """
    获取清理任务状态信息

    Args:
        _: 内部认证验证

    Returns:
        清理任务状态信息
    """
    return {
        "message": "清理任务服务运行正常",
        "supported_tasks": [
            "expired_drafts",
            "expired_pastes",
            "expired_members",
            "expired_uploads",
            "expired_user_sessions",
            "expired_used_refresh_tokens",
        ],
        "data_directory": settings.data_dir,
    }
