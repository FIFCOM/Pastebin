"""
Paste相关的Pydantic模型
"""

from datetime import datetime

from pydantic import BaseModel, Field, validator

# ===============================
# 请求模型
# ===============================


class PasteCreateRequest(BaseModel):
    """创建Paste请求"""

    encryption_mode: str = Field(
        ..., pattern="^(client|server)$", description="加密模式：client或server"
    )


class PasteTitleUpdateRequest(BaseModel):
    """更新Paste标题请求"""

    title: str = Field(..., max_length=255, description="Paste标题")


class PasteContentUpdateRequest(BaseModel):
    """更新Paste内容请求"""

    encrypted_content: str | None = Field(
        None, description="Base64编码的加密内容（客户端加密模式）"
    )
    content: str | None = Field(None, description="明文内容（服务端加密模式）")

    @validator("encrypted_content", "content")
    def validate_content_fields(cls, v, values):
        """验证内容字段"""
        # 至少有一个字段不为空
        encrypted_content = values.get("encrypted_content")
        content = v if v is not None else encrypted_content
        if not content:
            raise ValueError("必须提供encrypted_content或content")
        return v


class FileUploadRequest(BaseModel):
    """文件上传请求（JSON格式，用于客户端加密）"""

    encrypted_file: str = Field(..., description="Base64编码的加密文件数据")
    encrypted_metadata: dict = Field(..., description="加密的文件元数据")


class PastePublishRequest(BaseModel):
    """发布Paste请求"""

    settings: "PastePublishSettings" = Field(..., description="发布设置")


class PastePublishSettings(BaseModel):
    """Paste发布设置"""

    expire_time: str = Field(
        ...,
        pattern="^(7d|30d|1y|never)$",
        description="过期时间：7d, 30d, 1y, never",
    )
    max_views: int = Field(
        ..., ge=1, description="最大查看次数，1表示阅后即焚，-1表示无限制"
    )
    access_key: str | None = Field(None, description="访问密钥（可选）")

    @validator("max_views")
    def validate_max_views(cls, v):
        """验证max_views"""
        if v != -1 and v < 1:
            raise ValueError("max_views必须是-1（无限制）或大于0的正整数")
        return v


class PasteUpdateRequest(BaseModel):
    """更新Paste请求"""

    title: str | None = Field(None, max_length=255, description="新标题")
    expire_time: str | None = Field(
        None, pattern="^(7d|30d|1y|never)$", description="过期时间"
    )
    max_views: int | None = Field(None, ge=1, description="最大查看次数")
    access_key: str | None = Field(None, description="访问密钥，空字符串表示禁用")

    @validator("max_views")
    def validate_max_views(cls, v):
        """验证max_views"""
        if v is not None and v != -1 and v < 1:
            raise ValueError("max_views必须是-1（无限制）或大于0的正整数")
        return v


# ===============================
# 响应模型
# ===============================


class PasteCreateResponse(BaseModel):
    """创建Paste响应"""

    paste_id: str = Field(..., description="Paste ID")
    admin_key: str = Field(..., description="管理密钥")
    expires_at: datetime = Field(..., description="草稿过期时间")


class FileInfo(BaseModel):
    """文件信息"""

    id: str = Field(..., description="文件ID")
    size: int = Field(..., description="文件大小（字节）")
    encrypted_name: str = Field(..., description="加密的文件名（Base64）")
    url: str = Field(..., description="下载URL")


class PasteResponse(BaseModel):
    """Paste信息响应"""

    title: str | None = Field(None, description="Paste标题")
    status: str = Field(..., description="状态：published或edited")
    files: list[FileInfo] = Field(default=[], description="文件列表")
    published_at: datetime | None = Field(None, description="发布时间")
    updated_at: datetime = Field(..., description="更新时间")
    expire_at: datetime | None = Field(None, description="过期时间")
    view_count: int = Field(..., description="查看次数")
    max_views: int = Field(..., description="最大查看次数")

    class Config:
        from_attributes = True


class PasteContentResponse(BaseModel):
    """Paste内容响应"""

    encrypted_content: str = Field(..., description="加密内容（Base64）")
    content: str | None = Field(
        None, description="明文内容（如果提供了正确的解密密钥）"
    )


class PastePublishResponse(BaseModel):
    """发布Paste响应"""

    paste_id: str = Field(..., description="Paste ID")
    admin_key: str = Field(..., description="管理密钥")
    encryption_key: str | None = Field(
        None, description="加密密钥（当encryption_mode为server时返回）"
    )


class FileUploadResponse(BaseModel):
    """文件上传响应"""

    file_id: str = Field(..., description="文件ID")


# ===============================
# 工具函数
# ===============================


def get_expire_datetime(expire_time: str) -> datetime | None:
    """将expire_time字符串转换为datetime对象"""
    if expire_time == "never":
        return None

    from datetime import timedelta

    now = datetime.utcnow()
    if expire_time == "7d":
        return now + timedelta(days=7)
    elif expire_time == "30d":
        return now + timedelta(days=30)
    elif expire_time == "1y":
        return now + timedelta(days=365)
    else:
        raise ValueError(f"不支持的expire_time: {expire_time}")


# 更新前向引用
PastePublishRequest.model_rebuild()
