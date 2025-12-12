"""
用户Paste管理相关的Pydantic模型
"""

from datetime import datetime

from pydantic import BaseModel, Field

# ===============================
# 请求模型
# ===============================


class UserPasteSaveRequest(BaseModel):
    """将Paste保存到用户账户请求"""

    encryption_key: str = Field(..., description="paste密钥，将被用户密钥加密")
    admin_key: str = Field(..., description="管理权限令牌，用于验证权限")


class UserPasteStarRequest(BaseModel):
    """收藏/取消收藏Paste请求"""

    is_starred: bool = Field(..., description="是否收藏")


# ===============================
# 响应模型
# ===============================


class UserPasteInfo(BaseModel):
    """用户Paste信息"""

    paste_id: str = Field(..., description="Paste ID")
    status: str = Field(..., description="Paste状态：published或edited")
    title: str | None = Field(default=None, description="Paste标题")
    admin_key: str = Field(..., description="管理权限令牌")
    encryption_key: str = Field(..., description="paste密钥")
    max_views: int = Field(..., description="最大查看次数")
    view_count: int = Field(..., description="当前查看次数")
    is_starred: bool = Field(..., description="是否收藏")
    published_at: datetime | None = Field(default=None, description="发布时间")
    updated_at: datetime = Field(..., description="更新时间")
    expire_at: datetime | None = Field(default=None, description="过期时间")

    class Config:
        from_attributes = True


class UserPasteListResponse(BaseModel):
    """用户Paste列表响应"""

    pastes: list[UserPasteInfo] = Field(..., description="Paste列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页数量")


class UserPasteSearchParams(BaseModel):
    """用户Paste搜索参数"""

    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(10, ge=1, le=100, description="每页数量")
    status: str | None = Field(default=None, description="状态过滤：published|edited|all")
    starred: bool | None = Field(default=None, description="收藏状态过滤：true|false")
    search: str | None = Field(default=None, description="搜索关键词，搜索title")

    class Config:
        # 允许使用额外字段用于查询参数
        extra = "forbid"
