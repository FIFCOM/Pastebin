"""
管理员后台相关的 Pydantic 模型
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CleanupTaskName = Literal[
    "expired_drafts",
    "expired_pastes",
    "expired_members",
    "expired_uploads",
    "expired_user_sessions",
    "expired_used_refresh_tokens",
]


class AdminOverviewResponse(BaseModel):
    """管理员概览统计响应"""

    total_users: int = Field(..., description="用户总数")
    active_users: int = Field(..., description="活跃用户数")
    total_pastes: int = Field(..., description="Paste 总数")
    total_files: int = Field(..., description="文件总数")
    total_storage_bytes: int = Field(..., description="文件总大小（字节）")
    total_view_count: int = Field(..., description="Paste 内容累计读取次数")
    cleanup_counts: dict[CleanupTaskName, int] = Field(
        ..., description="各清理任务当前待处理数量"
    )


class AdminPasteListItem(BaseModel):
    """管理员 Paste 元数据列表项"""

    id: str
    title: str | None
    status: Literal["draft", "published", "edited"]
    type: Literal["txt", "md"]
    encryption_mode: Literal["client", "server"]
    creator_type: Literal["guest", "user"]
    creator_user_id: int | None
    creator_username: str | None
    creator_ip: str | None
    view_count: int
    max_views: int
    file_count: int
    file_total_size: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    expire_at: datetime | None


class AdminPasteListResponse(BaseModel):
    """管理员 Paste 元数据分页响应"""

    pastes: list[AdminPasteListItem]
    total: int
    page: int
    size: int


class AdminCleanupStatusResponse(BaseModel):
    """管理员清理任务状态响应"""

    supported_tasks: list[CleanupTaskName]
    cleanup_counts: dict[CleanupTaskName, int]
