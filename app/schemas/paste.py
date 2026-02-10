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


class FileUploadInitRequest(BaseModel):
    """分片上传初始化请求（二进制分片上传）"""

    encryption_mode: str | None = Field(
        default=None,
        pattern="^(client|server)$",
        description="加密模式：client或server（可选；不填则以Paste的encryption_mode为准）",
    )

    file_name: str = Field(
        ...,
        description="文件名（client: 建议传加密后的Base64；server: 明文，服务端会加密后落库）",
    )
    mime_type: str = Field(
        default="application/octet-stream",
        description="MIME类型",
    )
    file_size: int = Field(..., ge=0, description="原始文件大小（字节，未加密前）")

    requested_chunk_size: int | None = Field(
        default=None,
        ge=1,
        description="客户端期望的分片大小（字节）；服务端可能会调整",
    )


class FileUploadInitResponse(BaseModel):
    """分片上传初始化响应"""

    upload_id: str = Field(..., description="上传会话ID（也是最终file_id）")
    chunk_size: int = Field(..., description="服务端确认的分片大小（字节，按明文分片）")
    total_chunks: int = Field(..., description="总分片数")
    expires_at: datetime = Field(..., description="上传会话过期时间")
    max_total_upload_size: int = Field(
        ..., description="单个Paste的上传文件总大小上限（字节；0表示不限制）"
    )
    remaining_upload_size: int | None = Field(
        default=None,
        description="剩余可用上传容量（字节；当max_total_upload_size为0时为null）",
    )
    aad_prefix: str = Field(..., description="AAD前缀（版本化）")
    aad_required: bool = Field(..., description="是否强制AAD")
    iv_scheme: str = Field(..., description="nonce/iv方案说明")


class FileUploadStatusResponse(BaseModel):
    """分片上传状态响应（用于断点续传）"""

    upload_id: str = Field(..., description="上传会话ID（也是最终file_id）")
    encryption_mode: str = Field(..., description="加密模式：client或server")
    file_size: int = Field(..., description="原始文件大小（字节，未加密前）")
    chunk_size: int = Field(..., description="分片大小（字节，按明文分片）")
    total_chunks: int = Field(..., description="总分片数")
    expires_at: datetime = Field(..., description="上传会话过期时间")
    max_total_upload_size: int = Field(
        ..., description="单个Paste的上传文件总大小上限（字节；0表示不限制）"
    )
    remaining_upload_size: int | None = Field(
        default=None,
        description="剩余可用上传容量（字节；当max_total_upload_size为0时为null）",
    )

    uploaded_chunks: list[int] = Field(
        default_factory=list, description="已上传分片索引列表（升序）"
    )
    uploaded_count: int = Field(..., description="已上传分片数量")
    next_index: int = Field(
        ..., description="建议继续上传的下一个分片索引（若已齐全则等于total_chunks）"
    )
    completed: bool = Field(..., description="分片是否已全部上传完成（尚未complete也可能为true）")


class FileUploadCompleteRequest(BaseModel):
    """分片上传完成请求"""

    checksum_sha256: str | None = Field(
        default=None, description="可选：原始文件 SHA256（十六进制）"
    )
    chunk_hashes_sha256: list[str] | None = Field(
        default=None,
        description="可选：每个分片的SHA256（十六进制，按index顺序；server模式为明文分片，client模式为加密分片）",
    )

    @field_validator("checksum_sha256")
    @classmethod
    def validate_sha256_hex(cls, v: str | None):
        if v is None or v == "":
            return None
        vv = v.strip().lower()
        if len(vv) != 64 or any(ch not in "0123456789abcdef" for ch in vv):
            raise ValueError("checksum_sha256必须为64位十六进制字符串")
        return vv

    @field_validator("chunk_hashes_sha256")
    @classmethod
    def validate_chunk_hashes(cls, v: list[str] | None):
        if v is None:
            return None
        if len(v) == 0:
            raise ValueError("chunk_hashes_sha256不能为空列表")
        out: list[str] = []
        for item in v:
            if not item or not str(item).strip():
                raise ValueError("chunk_hashes_sha256包含空值")
            vv = str(item).strip().lower()
            if len(vv) != 64 or any(ch not in "0123456789abcdef" for ch in vv):
                raise ValueError("chunk_hashes_sha256必须为64位十六进制字符串数组")
            out.append(vv)
        return out


class FileUploadCompleteResponse(BaseModel):
    """分片上传完成响应"""

    file_id: str = Field(..., description="文件ID")
    max_total_upload_size: int = Field(
        ..., description="单个Paste的上传文件总大小上限（字节；0表示不限制）"
    )
    remaining_upload_size: int | None = Field(
        default=None,
        description="剩余可用上传容量（字节；当max_total_upload_size为0时为null）",
    )


class FileManifestResponse(BaseModel):
    """分片文件manifest响应（用于流式解密）"""

    version: int = Field(..., description="manifest版本")
    paste_id: str = Field(..., description="Paste ID")
    file_id: str = Field(..., description="文件ID")
    encryption_mode: str = Field(..., description="加密模式：client或server")
    plain_size: int = Field(..., description="原始文件大小（字节）")
    chunk_size: int = Field(..., description="分片大小（字节）")
    total_chunks: int = Field(..., description="分片总数")
    chunk_overhead_bytes: int = Field(..., description="每个分片的加密额外开销（字节）")
    chunk_format: str = Field(..., description="分片加密格式说明")
    aad_format: str = Field(..., description="AAD格式模板")
    aad_prefix: str | None = Field(
        default=None, description="AAD前缀（从aad_format推导）"
    )
    aad_required: bool = Field(..., description="是否强制AAD")
    iv_scheme: str = Field(..., description="IV方案说明")
    iv_prefix: str | None = Field(
        default=None, description="IV前缀（Base64编码，8字节）"
    )


class FileMetaResponse(BaseModel):
    """文件元信息（不包含任何解密密钥；用于前端客户端解密下载/预览）"""

    paste_id: str = Field(..., description="Paste ID")
    file_id: str = Field(..., description="文件ID")
    encrypted_name: str = Field(..., description="加密的文件名（Base64）")
    mime_type: str = Field(..., description="MIME类型")
    encrypted_size: int = Field(..., description="加密后文件大小（字节）")
    created_at: datetime = Field(..., description="上传时间（UTC）")
    plain_size: int | None = Field(
        default=None, description="原始文件大小（字节；manifest存在时返回）"
    )
    url: str = Field(..., description="文件下载URL（不包含任何密钥）")
    manifest_url: str = Field(..., description="manifest URL")


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
    max_views: int | None = Field(
        default=None, description="最大查看次数（-1表示无限制，其余需>=1）"
    )
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
    max_total_upload_size: int = Field(
        ..., description="单个Paste的上传文件总大小上限（字节；0表示不限制）"
    )
    remaining_upload_size: int | None = Field(
        default=None,
        description="剩余可用上传容量（字节；当max_total_upload_size为0时为null）",
    )
    timestamp: int = Field(..., description="响应时间戳（秒）")


class FileInfo(BaseModel):
    """文件信息"""

    id: str = Field(..., description="文件ID")
    size: int = Field(..., description="文件大小（字节）")
    encrypted_name: str | None = Field(
        default=None, description="加密的文件名（Base64；未提供解密密钥时返回）"
    )
    name: str | None = Field(
        default=None, description="解密后的文件名（提供正确的解密密钥时返回）"
    )
    url: str = Field(..., description="下载URL（不包含任何密钥）")
    plain_size: int | None = Field(
        default=None, description="原始文件大小（字节；分片上传时可用）"
    )


class PasteResponse(BaseModel):
    """Paste信息响应"""

    title: str | None = Field(default=None, description="Paste标题")
    type: str = Field(..., description="Paste类型：txt或md")
    status: str = Field(..., description="状态：published或edited")
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
    files: list[FileInfo] | None = Field(default=None, description="文件列表（可选）")


class PastePublishResponse(BaseModel):
    """发布Paste响应"""

    paste_id: str = Field(..., description="Paste ID")
    admin_key: str = Field(..., description="管理密钥")
    encryption_key: str | None = Field(
        default=None, description="加密密钥（当encryption_mode为server时返回）"
    )
    timestamp: int = Field(..., description="响应时间戳（秒）")


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
