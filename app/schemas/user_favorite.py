"""
用户收藏Paste相关的Pydantic模型
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _validate_access_key_bytes(value: str | None) -> str | None:
    if value and len(value.encode("utf-8")) > 72:
        raise ValueError("access_key不能超过72字节")
    return value


# ===============================
# 请求模型
# ===============================


class UserFavoriteSaveRequest(BaseModel):
    """保存Paste收藏请求"""

    encryption_key: str = Field(..., description="paste解密密钥，将被用户密钥加密")
    access_key: str | None = Field(
        default=None,
        max_length=72,
        description="访问密钥（可选，仅用于本次授权校验，不保存）",
    )

    @field_validator("access_key")
    @classmethod
    def validate_access_key(cls, v: str | None) -> str | None:
        """验证access_key长度"""
        return _validate_access_key_bytes(v)


class GuestFavoriteItem(BaseModel):
    """游客收藏条目（导入时使用）"""

    paste_id: str = Field(..., description="Paste ID")
    encryption_key: str = Field(..., description="paste解密密钥")
    access_key: str | None = Field(
        default=None,
        max_length=72,
        description="访问密钥（可选，仅用于导入授权校验，不保存）",
    )

    @field_validator("access_key")
    @classmethod
    def validate_access_key(cls, v: str | None) -> str | None:
        """验证access_key长度"""
        return _validate_access_key_bytes(v)


class ImportGuestFavoritesRequest(BaseModel):
    """导入游客收藏请求"""

    items: list[GuestFavoriteItem] = Field(..., description="游客收藏条目列表")


# ===============================
# 响应模型
# ===============================


class UserFavoriteListItem(BaseModel):
    """用户收藏列表条目（不含明文密钥）"""

    paste_id: str = Field(..., description="Paste ID")
    status: str = Field(..., description="Paste状态：published或edited")
    title: str | None = Field(default=None, description="Paste标题")
    max_views: int = Field(..., description="最大查看次数")
    view_count: int = Field(..., description="当前查看次数")
    published_at: datetime | None = Field(default=None, description="发布时间")
    paste_updated_at: datetime = Field(..., description="Paste更新时间")
    favorite_updated_at: datetime = Field(..., description="收藏更新时间")
    expire_at: datetime | None = Field(default=None, description="过期时间")

    class Config:
        from_attributes = True


class UserFavoriteDetail(UserFavoriteListItem):
    """用户收藏详情（含解密后的paste密钥）"""

    encryption_key: str = Field(..., description="paste解密密钥（解密后）")


class UserFavoriteListResponse(BaseModel):
    """用户收藏列表响应"""

    items: list[UserFavoriteListItem] = Field(..., description="收藏列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页数量")


class ImportGuestFavoritesResponse(BaseModel):
    """导入游客收藏响应"""

    imported: int = Field(..., description="成功导入条数")
    imported_ids: list[str] = Field(
        default_factory=list, description="成功导入的paste_id列表"
    )
    skipped: int = Field(..., description="跳过条数")
    errors: list[str] = Field(default_factory=list, description="失败原因摘要")
    snapshot: UserFavoriteListResponse = Field(..., description="导入后的最新收藏快照")


class UserFavoriteSearchParams(BaseModel):
    """用户收藏搜索参数"""

    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(20, ge=1, le=100, description="每页数量")
    search: str | None = Field(default=None, description="搜索关键词，搜索title")

    class Config:
        extra = "forbid"
