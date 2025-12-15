"""
Paste相关的Pydantic模型
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator

# ===============================
# 请求模型
# ===============================


class PasteCreateRequest(BaseModel):
    """创建Paste请求"""

    encryption_mode: str = Field(
        ..., pattern="^(client|server)$", description="加密模式：client或server"
    )


class PasteContentUpdateRequest(BaseModel):
    """更新Paste内容请求"""

    encrypted_content: str | None = Field(
        None, description="Base64编码的加密内容（客户端加密模式）"
    )
    content: str | None = Field(default=None, description="明文内容（服务端加密模式）")

    @field_validator("encrypted_content", "content", mode="after")
    @classmethod
    def validate_content_fields(cls, v, info):
        """验证内容字段"""
        # 至少有一个字段不为空
        if info.field_name == "content":
            # 当验证content字段时，检查是否至少有一个字段不为空
            encrypted_content = info.data.get("encrypted_content")
            if not v and not encrypted_content:
                raise ValueError("必须提供encrypted_content或content")
        return v


class FileUploadRequest(BaseModel):
    """文件上传请求（统一接口）"""

    encryption_mode: str | None = Field(
        default=None,
        pattern="^(client|server)$",
        description="加密模式：client或server（可选；不填则以Paste的encryption_mode为准）",
    )

    encrypted_file: str = Field(
        ...,
        description="Base64编码的文件数据（client: 加密后；server: 明文，服务端会加密后落盘）",
    )
    encrypted_metadata: dict = Field(
        ...,
        description="文件元数据（client: 可加密；server: 明文，服务端会加密file_name）",
    )


class PastePublishRequest(BaseModel):
    """发布Paste请求"""

    settings: "PastePublishSettings" = Field(..., description="发布设置")


class PastePublishSettings(BaseModel):
    """Paste发布设置"""

    title: str = Field(..., max_length=255, description="Paste标题")
    type: str = Field(
        "txt", pattern="^(txt|md)$", description="Paste类型：txt或md，默认为txt"
    )
    expire_time: str = Field(
        ...,
        pattern="^(7d|30d|1y|never)$",
        description="过期时间：7d, 30d, 1y, never",
    )
    max_views: int = Field(..., description="最大查看次数，1表示阅后即焚，-1表示无限制")
    access_key: str | None = Field(
        default=None, max_length=72, description="访问密钥（可选，最多72字符）"
    )

    @field_validator("max_views")
    @classmethod
    def validate_max_views(cls, v):
        """验证max_views"""
        if v != -1 and v < 1:
            raise ValueError("max_views必须是-1（无限制）或大于0的正整数")
        return v

    @field_validator("access_key")
    @classmethod
    def validate_access_key(cls, v):
        """验证access_key长度"""
        if v and len(v.encode("utf-8")) > 72:
            raise ValueError("access_key不能超过72字节")
        return v


class PasteUpdateRequest(BaseModel):
    """更新Paste请求"""

    title: str | None = Field(default=None, max_length=255, description="新标题")
    type: str | None = Field(
        None, pattern="^(txt|md)$", description="Paste类型：txt或md"
    )
    expire_time: str | None = Field(
        None, pattern="^(7d|30d|1y|never)$", description="过期时间"
    )
    max_views: int | None = Field(default=None, ge=1, description="最大查看次数")
    access_key: str | None = Field(
        default=None, description="访问密钥，空字符串表示禁用"
    )

    @field_validator("max_views")
    @classmethod
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
    timestamp: int = Field(..., description="响应时间戳（秒）")


class FileInfo(BaseModel):
    """文件信息"""

    id: str = Field(..., description="文件ID")
    size: int = Field(..., description="文件大小（字节）")
    encrypted_name: str = Field(..., description="加密的文件名（Base64）")
    url: str = Field(..., description="下载URL")


class PasteResponse(BaseModel):
    """Paste信息响应"""

    title: str | None = Field(default=None, description="Paste标题")
    type: str = Field(..., description="Paste类型：txt或md")
    status: str = Field(..., description="状态：published或edited")
    files: list[FileInfo] = Field(default=[], description="文件列表")
    published_at: datetime | None = Field(default=None, description="发布时间")
    updated_at: datetime = Field(..., description="更新时间")
    expire_at: datetime | None = Field(default=None, description="过期时间")
    view_count: int = Field(..., description="查看次数")
    max_views: int = Field(..., description="最大查看次数")

    class Config:
        from_attributes = True


class PasteContentResponse(BaseModel):
    """Paste内容响应"""

    encrypted_content: str | None = Field(
        default=None, description="加密内容（Base64）"
    )
    content: str | None = Field(
        default=None, description="明文内容（如果提供了正确的解密密钥）"
    )


class PastePublishResponse(BaseModel):
    """发布Paste响应"""

    paste_id: str = Field(..., description="Paste ID")
    admin_key: str = Field(..., description="管理密钥")
    encryption_key: str | None = Field(
        default=None, description="加密密钥（当encryption_mode为server时返回）"
    )
    timestamp: int = Field(..., description="响应时间戳（秒）")


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

    now = datetime.now(UTC)
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
