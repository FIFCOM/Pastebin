"""
用户History管理相关的Pydantic模型
"""

from datetime import datetime

from pydantic import BaseModel, Field

# ===============================
# 请求模型
# ===============================


class UserHistorySaveRequest(BaseModel):
    """将Paste保存到用户账户请求"""

    encryption_key: str = Field(..., description="paste密钥，将被用户密钥加密")
    admin_key: str = Field(..., description="管理权限令牌，用于验证权限")


class GuestHistoryItem(BaseModel):
    """游客历史条目（导入时使用）"""

    paste_id: str = Field(..., description="Paste ID")
    admin_key: str = Field(..., description="管理权限令牌")
    encryption_key: str = Field(..., description="paste密钥")


class ImportGuestHistoryRequest(BaseModel):
    """导入游客历史请求"""

    items: list[GuestHistoryItem] = Field(..., description="游客历史条目列表")


# ===============================
# 响应模型
# ===============================


class UserHistoryListItem(BaseModel):
    """用户History列表条目（不含明文密钥）"""

    paste_id: str = Field(..., description="Paste ID")
    status: str = Field(..., description="Paste状态：published或edited")
    title: str | None = Field(default=None, description="Paste标题")
    max_views: int = Field(..., description="最大查看次数")
    view_count: int = Field(..., description="当前查看次数")
    published_at: datetime | None = Field(default=None, description="发布时间")
    paste_updated_at: datetime = Field(..., description="Paste更新时间")
    history_updated_at: datetime = Field(..., description="历史记录更新时间")
    expire_at: datetime | None = Field(default=None, description="过期时间")

    class Config:
        from_attributes = True


class UserHistoryDetail(BaseModel):
    """用户History详情（含解密后的密钥，按需返回）"""

    paste_id: str = Field(..., description="Paste ID")
    status: str = Field(..., description="Paste状态：published或edited")
    title: str | None = Field(default=None, description="Paste标题")
    admin_key: str = Field(..., description="管理权限令牌（解密后）")
    encryption_key: str = Field(..., description="paste密钥（解密后）")
    max_views: int = Field(..., description="最大查看次数")
    view_count: int = Field(..., description="当前查看次数")
    published_at: datetime | None = Field(default=None, description="发布时间")
    paste_updated_at: datetime = Field(..., description="Paste更新时间")
    history_updated_at: datetime = Field(..., description="历史记录更新时间")
    expire_at: datetime | None = Field(default=None, description="过期时间")

    class Config:
        from_attributes = True


class UserHistoryListResponse(BaseModel):
    """用户History列表响应"""

    items: list[UserHistoryListItem] = Field(..., description="历史记录列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页数量")


class ImportGuestHistoryResponse(BaseModel):
    """导入游客历史响应"""

    imported: int = Field(..., description="成功导入条数")
    imported_ids: list[str] = Field(
        default_factory=list, description="成功导入的paste_id列表"
    )
    skipped: int = Field(..., description="跳过条数")
    errors: list[str] = Field(default_factory=list, description="失败原因摘要")
    snapshot: UserHistoryListResponse = Field(..., description="导入后的最新历史快照")


class UserHistorySearchParams(BaseModel):
    """用户History搜索参数"""

    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(20, ge=1, le=100, description="每页数量")
    search: str | None = Field(default=None, description="搜索关键词，搜索title")

    class Config:
        extra = "forbid"
