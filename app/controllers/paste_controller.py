"""
Paste控制器 - REST API路由
"""

import io
import time
from datetime import datetime
from typing import cast
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.dependencies import get_optional_user_strict
from app.core.request_meta import extract_client_ip
from app.core.time_utils import is_expired
from app.schemas.common import MessageResponse
from app.schemas.paste import (
    FileManifestResponse,
    FileMetaResponse,
    FileUploadCompleteRequest,
    FileUploadCompleteResponse,
    FileUploadInitRequest,
    FileUploadInitResponse,
    FileUploadStatusResponse,
    PasteContentResponse,
    PasteContentUpdateRequest,
    PasteCreateRequest,
    PasteCreateResponse,
    PastePublishRequest,
    PastePublishResponse,
    PasteResponse,
    PasteUpdateRequest,
)
from app.schemas.user import UserResponse
from app.services.paste_service import PasteService

# 创建路由器
router = APIRouter(prefix="/api/pastes", tags=["Paste"])


def _build_content_disposition(
    filename: str, fallback_filename: str = "encrypted_file"
) -> str:
    """
    构造安全的 Content-Disposition 头，避免 CRLF 注入，并尽量兼容非 ASCII 文件名。

    返回格式示例：
    attachment; filename="fallback.txt"; filename*=UTF-8''%E4%B8%AD%E6%96%87.txt
    """
    from pathlib import Path

    def _sanitize_name(value: str) -> str:
        # 只保留文件名，避免路径穿透/分隔符
        name = str(Path(value).name)

        # 移除可能造成响应头注入的字符
        name = name.replace("\r", "_").replace("\n", "_").replace("\x00", "_")

        # 替换不可见控制字符
        name = "".join((ch if ord(ch) >= 32 and ord(ch) != 127 else "_") for ch in name)

        # 避免破坏 quoted-string
        name = name.replace("\\", "_").replace('"', "'").strip()
        if not name:
            return ""

        # 限制长度，避免异常超长 header
        return name[:200]

    safe_fallback = _sanitize_name(fallback_filename) or "encrypted_file"

    name = _sanitize_name(filename) or safe_fallback

    ascii_fallback = name.encode("ascii", "ignore").decode("ascii").strip()
    if not ascii_fallback:
        ascii_fallback = safe_fallback.encode("ascii", "ignore").decode("ascii").strip()
        if not ascii_fallback:
            ascii_fallback = "encrypted_file"
    ascii_fallback = ascii_fallback.replace("\\", "_").replace('"', "'")[:200]

    # RFC 5987 (filename*)：UTF-8 + percent-encoding
    encoded = quote(name, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


def _iter_file(path, chunk_size: int = 1024 * 1024):
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def _iter_file_range(path, start: int, end: int, chunk_size: int = 1024 * 1024):
    remaining = end - start + 1
    if remaining <= 0:
        return
    with open(path, "rb") as f:
        f.seek(start)
        while remaining > 0:
            chunk = f.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def _parse_range_header(range_header: str | None, size: int) -> tuple[int, int] | None:
    """
    Parse a single HTTP Range header (bytes only).

    Returns (start, end) inclusive, or None if header is missing/unsupported.
    Raises HTTPException(416) for invalid/unsatisfiable ranges.
    """
    if range_header is None:
        return None
    value = str(range_header).strip()
    if value == "":
        return None

    if not value.lower().startswith("bytes="):
        return None

    if size < 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件大小无效",
        )

    # We support a single range. If multiple are provided, take the first one.
    spec = value[6:].strip()
    if "," in spec:
        spec = spec.split(",", 1)[0].strip()

    if "-" not in spec:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="无效Range格式",
            headers={"Content-Range": f"bytes */{size}"},
        )

    start_str, end_str = spec.split("-", 1)

    if size == 0:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="空文件不支持Range",
            headers={"Content-Range": "bytes */0"},
        )

    if start_str == "":
        # suffix-byte-range-spec: bytes=-N
        try:
            suffix_len = int(end_str, 10)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="无效Range格式",
                headers={"Content-Range": f"bytes */{size}"},
            ) from None
        if suffix_len <= 0:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="无效Range长度",
                headers={"Content-Range": f"bytes */{size}"},
            )
        if suffix_len >= size:
            return (0, size - 1)
        return (size - suffix_len, size - 1)

    try:
        start = int(start_str, 10)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="无效Range起点",
            headers={"Content-Range": f"bytes */{size}"},
        ) from None

    if start < 0:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="无效Range起点",
            headers={"Content-Range": f"bytes */{size}"},
        )

    if start >= size:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Range超出文件大小",
            headers={"Content-Range": f"bytes */{size}"},
        )

    if end_str == "":
        end = size - 1
    else:
        try:
            end = int(end_str, 10)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="无效Range终点",
                headers={"Content-Range": f"bytes */{size}"},
            ) from None

    if end < start:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="无效Range区间",
            headers={"Content-Range": f"bytes */{size}"},
        )

    if end >= size:
        end = size - 1

    return (start, end)


def _get_admin_key_from_header(x_paste_admin_key: str | None) -> str:
    """从X-Paste-Admin-Key头中读取admin_key。"""
    if not x_paste_admin_key or not x_paste_admin_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少X-Paste-Admin-Key头",
        )

    return x_paste_admin_key.strip()


def _try_get_admin_key_from_header(x_paste_admin_key: str | None) -> str | None:
    """尝试从X-Paste-Admin-Key头中读取admin_key。"""
    if not x_paste_admin_key:
        return None
    v = x_paste_admin_key.strip()
    if not v:
        return None
    return v


@router.post(
    "", response_model=PasteCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_paste(
    request: Request,
    paste_data: PasteCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse | None = Depends(get_optional_user_strict),
):
    """
    创建新Paste（草稿状态）

    - **encryption_mode**: 加密模式，client（客户端加密）或server（服务端加密）
    """
    try:
        return PasteService.create_paste(
            db,
            paste_data,
            creator_user_id=current_user.id if current_user else None,
            creator_ip=extract_client_ip(request),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.post("/{paste_id}/content", response_model=MessageResponse)
async def update_paste_content(
    paste_id: str,
    content_data: PasteContentUpdateRequest,
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    encryption_key: str | None = Header(
        None, alias="X-Encryption-Key", description="服务端加密模式下用于加密写入的密钥"
    ),
    db: Session = Depends(get_db),
):
    """
    上传/更新Paste内容

    需要在X-Paste-Admin-Key头中提供admin_key

    - **encrypted_content**: Base64编码的加密内容（客户端加密模式）
    - **content**: 明文内容（服务端加密模式）
    """
    admin_key = _get_admin_key_from_header(x_paste_admin_key)

    try:
        PasteService.update_paste_content(
            db, paste_id, admin_key, content_data, encryption_key=encryption_key
        )
        return MessageResponse(message="内容更新成功", timestamp=int(time.time()))
    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.post("/{paste_id}/files/init", response_model=FileUploadInitResponse)
async def init_file_upload(
    paste_id: str,
    body: FileUploadInitRequest,
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    encryption_key: str | None = Header(
        None, alias="X-Encryption-Key", description="服务端加密模式下用于加密写入的密钥"
    ),
    db: Session = Depends(get_db),
):
    """
    初始化分片上传会话

    返回 upload_id / chunk_size / total_chunks。
    分片上传使用二进制 PUT，不要再使用 JSON Base64。
    """
    admin_key = _get_admin_key_from_header(x_paste_admin_key)
    try:
        return PasteService.init_file_upload(
            db, paste_id, admin_key, body, encryption_key=encryption_key
        )
    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.get(
    "/{paste_id}/files/{upload_id}/status", response_model=FileUploadStatusResponse
)
async def get_file_upload_status(
    paste_id: str,
    upload_id: str,
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    db: Session = Depends(get_db),
):
    """
    获取分片上传状态（用于断点续传）

    需要在X-Paste-Admin-Key头中提供admin_key
    """
    admin_key = _get_admin_key_from_header(x_paste_admin_key)
    try:
        return PasteService.get_file_upload_status(db, paste_id, upload_id, admin_key)
    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        elif "过期" in str(e):
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.put(
    "/{paste_id}/files/{upload_id}/chunk/{index}", response_model=MessageResponse
)
async def upload_file_chunk(
    paste_id: str,
    upload_id: str,
    index: int,
    request: Request,
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    db: Session = Depends(get_db),
):
    """
    上传单个分片（二进制）

    Content-Type: application/octet-stream
    """
    admin_key = _get_admin_key_from_header(x_paste_admin_key)
    try:
        # 准备上传：验证权限、Session状态，计算预期参数
        prep = PasteService.prepare_chunk_upload(
            db, paste_id, upload_id, index, admin_key
        )
        chunk_path = prep["chunk_path"]
        expected_len = prep["expected_len"]
        expected_iv = prep["expected_iv"]
        encryption_mode = prep["encryption_mode"]

        import secrets as _secrets

        tmp_path = chunk_path.with_suffix(
            chunk_path.suffix + f".tmp.{_secrets.token_hex(8)}"
        )

        received = 0
        pending = bytearray()
        iv_validated = encryption_mode != "client"
        try:
            with open(tmp_path, "wb") as f:
                async for part in request.stream():
                    received += len(part)
                    if received > expected_len:
                        raise ValueError("分片过大")

                    if not iv_validated:
                        need = 12 - len(pending)
                        pending.extend(part[:need])
                        rest = part[need:]
                        if len(pending) == 12:
                            if expected_iv is None:
                                raise ValueError("上传会话IV前缀缺失")
                            if bytes(pending) != expected_iv:
                                raise ValueError("分片IV不匹配")
                            iv_validated = True
                            f.write(pending)
                            pending.clear()
                            if rest:
                                f.write(rest)
                        continue

                    f.write(part)
        except Exception:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise

        if not iv_validated:
            raise ValueError("分片数据不足")

        if received != expected_len:
            raise ValueError(f"分片大小不匹配: expected={expected_len}, got={received}")

        # 原子落盘（若并发写同一分片，避免 silent overwrite）
        try:
            tmp_path.replace(chunk_path)
        except FileExistsError:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise ValueError("分片已存在") from None

        return MessageResponse(message="分片上传成功", timestamp=int(time.time()))

    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        elif "过期" in str(e):
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分片上传失败: {str(e)}",
        ) from None


@router.post(
    "/{paste_id}/files/{upload_id}/complete", response_model=FileUploadCompleteResponse
)
async def complete_file_upload(
    paste_id: str,
    upload_id: str,
    body: FileUploadCompleteRequest,
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    encryption_key: str | None = Header(
        None, alias="X-Encryption-Key", description="服务端加密模式下用于加密写入的密钥"
    ),
    db: Session = Depends(get_db),
):
    """
    完成分片上传并落盘
    """
    admin_key = _get_admin_key_from_header(x_paste_admin_key)
    try:
        return PasteService.complete_file_upload(
            db, paste_id, upload_id, admin_key, body, encryption_key=encryption_key
        )
    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        elif "过期" in str(e):
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.post("/{paste_id}/files/{upload_id}/abort", response_model=MessageResponse)
async def abort_file_upload(
    paste_id: str,
    upload_id: str,
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    db: Session = Depends(get_db),
):
    """
    取消分片上传并清理临时数据
    """
    admin_key = _get_admin_key_from_header(x_paste_admin_key)
    try:
        PasteService.abort_file_upload(db, paste_id, upload_id, admin_key)
        return MessageResponse(message="上传已取消", timestamp=int(time.time()))
    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.delete("/{paste_id}/files/{file_id}", response_model=MessageResponse)
async def delete_file(
    paste_id: str,
    file_id: str,
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    db: Session = Depends(get_db),
):
    """
    删除文件

    需要在X-Paste-Admin-Key头中提供admin_key
    """
    admin_key = _get_admin_key_from_header(x_paste_admin_key)

    try:
        PasteService.delete_file(db, paste_id, file_id, admin_key)
        return MessageResponse(message="文件删除成功")
    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.post("/{paste_id}/publish", response_model=PastePublishResponse)
async def publish_paste(
    paste_id: str,
    publish_data: PastePublishRequest,
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    db: Session = Depends(get_db),
):
    """
    发布Paste

    需要在X-Paste-Admin-Key头中提供admin_key

    - **expire_time**: 过期时间（7d, 30d, 1y, never）
    - **max_views**: 最大查看次数（1表示阅后即焚，-1表示无限制）
    - **access_key**: 访问密钥（可选）
    """
    admin_key = _get_admin_key_from_header(x_paste_admin_key)

    try:
        return PasteService.publish_paste(db, paste_id, admin_key, publish_data)
    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.get("/{paste_id}", response_model=PasteResponse)
async def get_paste_info(
    paste_id: str,
    access_key: str | None = Query(None, description="访问密钥（可选）"),
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    db: Session = Depends(get_db),
):
    """
    获取Paste信息

    - **access_key**: 访问密钥（如果Paste设置了访问密钥则需要提供）
    """
    admin_key = _try_get_admin_key_from_header(x_paste_admin_key)
    try:
        return PasteService.get_paste_info(
            db, paste_id, access_key, admin_key=admin_key
        )
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        elif "访问密钥" in str(e) or "权限" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "过期" in str(e) or "次数" in str(e):
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.get(
    "/{paste_id}/content",
    response_model=PasteContentResponse,
    response_model_exclude_none=True,
)
async def get_paste_content(
    paste_id: str,
    access_key: str | None = Query(None, description="访问密钥（可选）"),
    encryption_key: str | None = Query(None, description="解密密钥（可选）"),
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    db: Session = Depends(get_db),
):
    """
    获取Paste内容

    - **access_key**: 访问密钥（如果Paste设置了访问密钥则需要提供）
    - **encryption_key**: 解密密钥（可选，如果提供且正确则返回解密后的内容）
    """
    admin_key = _try_get_admin_key_from_header(x_paste_admin_key)
    try:
        return PasteService.get_paste_content(
            db,
            paste_id,
            access_key,
            encryption_key,
            admin_key=admin_key,
        )
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        elif "访问密钥" in str(e) or "权限" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "过期" in str(e):
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.get(
    "/{paste_id}/files/{file_id}/manifest",
    response_model=FileManifestResponse,
    response_model_exclude_none=True,
)
async def get_file_manifest(
    paste_id: str,
    file_id: str,
    access_key: str | None = Query(None, description="访问密钥（可选）"),
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    db: Session = Depends(get_db),
):
    """
    获取分片文件manifest（用于流式解密）

    - **access_key**: 访问密钥（如果Paste设置了访问密钥则需要提供）
    """
    try:
        import json
        from pathlib import Path

        from app.models.paste import File, Paste
        from config.config import settings

        # 检查 Paste 状态/权限/过期/阅后即焚
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Paste不存在或不可访问"
            )

        admin_key = _try_get_admin_key_from_header(x_paste_admin_key)
        admin_ok = bool(admin_key and PasteService._verify_admin_key(paste, admin_key))

        if str(paste.status) == "draft" and not admin_ok:  # type: ignore
            if admin_key is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="管理密钥错误"
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Paste不存在或不可访问"
            )

        if not admin_ok and not PasteService._verify_access_key(paste, access_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="访问密钥错误"
            )

        paste_expire_at: datetime | None = cast(datetime | None, paste.expire_at)
        if is_expired(paste_expire_at):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Paste已过期")

        if not admin_ok:
            paste_max_views = int(paste.max_views or -1)  # type: ignore
            paste_view_count = int(paste.view_count or 0)  # type: ignore
            if paste_max_views > 0 and paste_view_count >= paste_max_views:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE, detail="Paste已达到最大查看次数"
                )

        # 获取文件记录
        file_record = (
            db.query(File).filter(File.id == file_id, File.paste_id == paste_id).first()
        )

        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在"
            )

        manifest_path = (
            Path(settings.data_dir) / "files" / paste_id / f"{file_id}.manifest.json"
        )
        if not manifest_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="manifest不存在（非分片文件）",
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        def _require_int(key: str) -> int:
            value = manifest.get(key)
            if value is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"manifest缺少字段: {key}",
                )
            try:
                return int(value)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"manifest字段无效: {key}",
                ) from None

        def _require_str(key: str) -> str:
            value = manifest.get(key)
            if value is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"manifest缺少字段: {key}",
                )
            return str(value)

        version = _require_int("version")
        encryption_mode = _require_str("encryption_mode")
        plain_size = _require_int("plain_size")
        chunk_size = _require_int("chunk_size")
        total_chunks = _require_int("total_chunks")
        chunk_overhead_bytes = _require_int("chunk_overhead_bytes")
        chunk_format = _require_str("chunk_format")
        aad_format = _require_str("aad_format")
        aad_required = bool(manifest.get("aad_required", True))
        iv_scheme = _require_str("iv_scheme")
        iv_prefix_value = manifest.get("iv_prefix")
        iv_prefix = str(iv_prefix_value) if iv_prefix_value is not None else None

        aad_prefix: str | None
        if aad_format:
            aad_prefix = aad_format.split("|", 1)[0]
        else:
            aad_prefix = None

        return FileManifestResponse(
            version=version,
            paste_id=paste_id,
            file_id=file_id,
            encryption_mode=encryption_mode,
            plain_size=plain_size,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            chunk_overhead_bytes=chunk_overhead_bytes,
            chunk_format=chunk_format,
            aad_format=aad_format,
            aad_prefix=aad_prefix,
            aad_required=aad_required,
            iv_scheme=iv_scheme,
            iv_prefix=iv_prefix,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"manifest读取失败: {str(e)}",
        ) from None


@router.get(
    "/{paste_id}/files/{file_id}/meta",
    response_model=FileMetaResponse,
    response_model_exclude_none=True,
)
async def get_file_meta(
    paste_id: str,
    file_id: str,
    access_key: str | None = Query(None, description="访问密钥（可选）"),
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    db: Session = Depends(get_db),
):
    """
    获取文件元信息（不包含任何解密密钥；用于前端客户端解密下载/预览）。

    - **access_key**: 访问密钥（如果Paste设置了访问密钥则需要提供）
    """
    try:
        import json
        from pathlib import Path

        from app.models.paste import File, Paste
        from config.config import settings

        # 检查 Paste 状态/权限/过期/阅后即焚
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Paste不存在或不可访问"
            )

        admin_key = _try_get_admin_key_from_header(x_paste_admin_key)
        admin_ok = bool(admin_key and PasteService._verify_admin_key(paste, admin_key))

        if str(paste.status) == "draft" and not admin_ok:  # type: ignore
            if admin_key is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="管理密钥错误"
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Paste不存在或不可访问"
            )

        if not admin_ok and not PasteService._verify_access_key(paste, access_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="访问密钥错误"
            )

        paste_expire_at: datetime | None = cast(datetime | None, paste.expire_at)
        if is_expired(paste_expire_at):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Paste已过期")

        if not admin_ok:
            paste_max_views = int(paste.max_views or -1)  # type: ignore
            paste_view_count = int(paste.view_count or 0)  # type: ignore
            if paste_max_views > 0 and paste_view_count >= paste_max_views:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE, detail="Paste已达到最大查看次数"
                )

        file_record = (
            db.query(File).filter(File.id == file_id, File.paste_id == paste_id).first()
        )
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在"
            )

        # plain_size: 来自 manifest（若存在）
        plain_size: int | None = None
        manifest_path = (
            Path(settings.data_dir) / "files" / paste_id / f"{file_id}.manifest.json"
        )
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                value = manifest.get("plain_size")
                if value is not None:
                    plain_size = int(value)
            except Exception:
                plain_size = None

        return FileMetaResponse(
            paste_id=paste_id,
            file_id=file_id,
            encrypted_name=str(file_record.file_name_encrypted),  # type: ignore
            mime_type=str(file_record.mime_type) or "application/octet-stream",  # type: ignore
            encrypted_size=int(file_record.file_size),  # type: ignore
            created_at=file_record.created_at,  # type: ignore[arg-type]
            plain_size=plain_size,
            url=f"/api/pastes/{paste_id}/files/{file_id}",
            manifest_url=f"/api/pastes/{paste_id}/files/{file_id}/manifest",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件元信息读取失败: {str(e)}",
        ) from None


@router.get("/{paste_id}/files/{file_id}")
def get_file(
    paste_id: str,
    file_id: str,
    access_key: str | None = Query(None, description="访问密钥（可选）"),
    encryption_key: str | None = Query(None, description="解密密钥（可选）"),
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    range_header: str | None = Header(
        None, alias="Range", description="HTTP Range头（bytes=...）"
    ),
):
    """
    获取文件

    - **access_key**: 访问密钥（如果Paste设置了访问密钥则需要提供）
    - **encryption_key**: 解密密钥（可选，如果提供且正确则解密文件名和内容）

    返回文件流，Content-Disposition: attachment; filename="filename"
    """
    # 这个接口返回 StreamingResponse，响应体可能在路由函数返回后继续传输很久。
    # 这里手动管理 session，确保完成权限校验和文件元数据读取后尽快释放数据库连接。
    # 返回流之前需要把后续迭代器会用到的 ORM 字段转换成普通值，避免关闭 session 后再触发懒加载。
    db = SessionLocal()
    try:
        from app.models.paste import File, Paste
        from config.config import settings

        # 检查 Paste 状态/权限/过期/阅后即焚
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Paste不存在或不可访问"
            )

        admin_key = _try_get_admin_key_from_header(x_paste_admin_key)
        admin_ok = bool(admin_key and PasteService._verify_admin_key(paste, admin_key))

        if str(paste.status) == "draft" and not admin_ok:  # type: ignore
            if admin_key is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="管理密钥错误"
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Paste不存在或不可访问"
            )

        if not admin_ok and not PasteService._verify_access_key(paste, access_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="访问密钥错误"
            )

        paste_expire_at: datetime | None = cast(datetime | None, paste.expire_at)
        if is_expired(paste_expire_at):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Paste已过期")

        if not admin_ok:
            paste_max_views = int(paste.max_views or -1)  # type: ignore
            paste_view_count = int(paste.view_count or 0)  # type: ignore
            if paste_max_views > 0 and paste_view_count >= paste_max_views:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE, detail="Paste已达到最大查看次数"
                )

        # 获取文件记录
        file_record = (
            db.query(File).filter(File.id == file_id, File.paste_id == paste_id).first()
        )

        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在"
            )

        # 读取文件
        from pathlib import Path

        file_path = Path(settings.data_dir) / str(file_record.storage_path)  # type: ignore
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在"
            )

        # 获取文件名
        encrypted_filename = str(file_record.file_name_encrypted)  # type: ignore
        placeholder_filename = f"mb_encrypted_{file_id}"
        decrypted_filename: str | None = None

        key_bytes: bytes | None = None
        if encryption_key:
            try:
                from app.core.security import urlsafe_str_to_key

                key_bytes = urlsafe_str_to_key(encryption_key)
            except Exception:
                key_bytes = None

        if key_bytes is not None:
            try:
                from app.core.security import decrypt_with_key, str_to_bytes

                encrypted_name_bytes = str_to_bytes(encrypted_filename)
                decrypted_name_bytes = decrypt_with_key(encrypted_name_bytes, key_bytes)
                decrypted_filename = decrypted_name_bytes.decode(errors="replace")
            except Exception:
                decrypted_filename = None

        media_type = str(file_record.mime_type) or "application/octet-stream"  # type: ignore

        # 若提供了正确的解密密钥：尽可能解密后返回
        if key_bytes is not None:
            try:
                from app.core.security import decrypt_with_key

                # 分片上传：manifest 存在时可按chunk流式解密，避免一次性读入内存
                manifest_path = (
                    Path(settings.data_dir)
                    / "files"
                    / paste_id
                    / f"{file_id}.manifest.json"
                )
                if manifest_path.exists():
                    import json

                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    chunk_size = int(manifest.get("chunk_size"))
                    total_chunks = int(manifest.get("total_chunks"))
                    plain_size = int(manifest.get("plain_size"))
                    aad_required = bool(manifest.get("aad_required", True))
                    chunk_overhead_bytes = int(manifest.get("chunk_overhead_bytes", 28))
                    if chunk_overhead_bytes != 28:
                        raise ValueError("不支持的分片加密格式")
                    content_disposition = _build_content_disposition(
                        decrypted_filename or placeholder_filename,
                        fallback_filename=placeholder_filename,
                    )

                    byte_range = _parse_range_header(range_header, plain_size)
                    if byte_range is not None:
                        range_start, range_end = byte_range
                        start_chunk = range_start // chunk_size
                        end_chunk = range_end // chunk_size
                        start_in_chunk = range_start - start_chunk * chunk_size
                        end_in_chunk = range_end - end_chunk * chunk_size

                        def _iter_decrypted_range():
                            stride = chunk_size + chunk_overhead_bytes
                            with open(file_path, "rb") as f:
                                f.seek(start_chunk * stride)
                                for idx in range(start_chunk, end_chunk + 1):
                                    expected_plain = (
                                        chunk_size
                                        if idx < total_chunks - 1
                                        else plain_size
                                        - chunk_size * (total_chunks - 1)
                                    )
                                    if expected_plain < 0:
                                        expected_plain = 0
                                    iv = f.read(12)
                                    ciphertext = f.read(expected_plain + 16)
                                    if (
                                        len(iv) != 12
                                        or len(ciphertext) != expected_plain + 16
                                    ):
                                        raise ValueError("文件分片格式错误")

                                    encrypted_chunk = iv + ciphertext
                                    aad = PasteService._file_chunk_aad(
                                        paste_id, file_id, idx, total_chunks
                                    )
                                    if aad_required:
                                        plain = decrypt_with_key(
                                            encrypted_chunk, key_bytes, aad=aad
                                        )
                                    else:
                                        plain = decrypt_with_key(
                                            encrypted_chunk, key_bytes, aad=None
                                        )

                                    slice_start = (
                                        start_in_chunk if idx == start_chunk else 0
                                    )
                                    slice_end_exclusive = (
                                        end_in_chunk + 1
                                        if idx == end_chunk
                                        else len(plain)
                                    )
                                    chunk_out = plain[slice_start:slice_end_exclusive]
                                    if chunk_out:
                                        yield chunk_out

                        content_length = range_end - range_start + 1
                        content_range = f"bytes {range_start}-{range_end}/{plain_size}"
                        return StreamingResponse(
                            _iter_decrypted_range(),
                            status_code=status.HTTP_206_PARTIAL_CONTENT,
                            media_type=media_type,
                            headers={
                                "Content-Disposition": content_disposition,
                                "Content-Length": str(content_length),
                                "Content-Range": content_range,
                                "Accept-Ranges": "bytes",
                            },
                        )

                    def _iter_decrypted_chunks():
                        with open(file_path, "rb") as f:
                            for idx in range(total_chunks):
                                expected_plain = (
                                    chunk_size
                                    if idx < total_chunks - 1
                                    else plain_size - chunk_size * (total_chunks - 1)
                                )
                                if expected_plain < 0:
                                    expected_plain = 0
                                iv = f.read(12)
                                ciphertext = f.read(expected_plain + 16)
                                if (
                                    len(iv) != 12
                                    or len(ciphertext) != expected_plain + 16
                                ):
                                    raise ValueError("文件分片格式错误")

                                encrypted_chunk = iv + ciphertext
                                aad = PasteService._file_chunk_aad(
                                    paste_id, file_id, idx, total_chunks
                                )
                                if aad_required:
                                    yield decrypt_with_key(
                                        encrypted_chunk, key_bytes, aad=aad
                                    )
                                else:
                                    yield decrypt_with_key(
                                        encrypted_chunk, key_bytes, aad=None
                                    )

                    return StreamingResponse(
                        _iter_decrypted_chunks(),
                        media_type=media_type,
                        headers={
                            "Content-Disposition": content_disposition,
                            "Content-Length": str(plain_size),
                            "Accept-Ranges": "bytes",
                        },
                    )

                # 非分片：整体解密（AES-GCM需整体解密，存在内存开销）
                file_content = file_path.read_bytes()
                file_content = decrypt_with_key(file_content, key_bytes)
                content_disposition = _build_content_disposition(
                    decrypted_filename or placeholder_filename,
                    fallback_filename=placeholder_filename,
                )
                return StreamingResponse(
                    io.BytesIO(file_content),
                    media_type=media_type,
                    headers={
                        "Content-Disposition": content_disposition,
                        "Content-Length": str(len(file_content)),
                    },
                )
            except HTTPException:
                raise
            except Exception:
                # 解密失败，回退为返回原始加密内容（不强制把错误暴露给客户端）
                pass

        # 未提供/解密失败：直接流式返回原始文件，避免一次性读入内存
        file_size = file_path.stat().st_size
        byte_range = _parse_range_header(range_header, file_size)
        content_disposition = _build_content_disposition(
            placeholder_filename, fallback_filename=placeholder_filename
        )
        if byte_range is not None:
            range_start, range_end = byte_range
            content_length = range_end - range_start + 1
            content_range = f"bytes {range_start}-{range_end}/{file_size}"
            return StreamingResponse(
                _iter_file_range(file_path, range_start, range_end),
                status_code=status.HTTP_206_PARTIAL_CONTENT,
                media_type=media_type,
                headers={
                    "Content-Disposition": content_disposition,
                    "Content-Length": str(content_length),
                    "Content-Range": content_range,
                    "Accept-Ranges": "bytes",
                },
            )
        return StreamingResponse(
            _iter_file(file_path),
            media_type=media_type,
            headers={
                "Content-Disposition": content_disposition,
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件读取失败: {str(e)}",
        ) from None
    finally:
        db.close()


@router.put("/{paste_id}", response_model=MessageResponse)
async def update_paste(
    paste_id: str,
    update_data: PasteUpdateRequest,
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    db: Session = Depends(get_db),
):
    """
    更新Paste设置

    需要在X-Paste-Admin-Key头中提供admin_key

    - **title**: 新标题（可选）
    - **type**: Paste类型：txt或md（可选）
    - **expire_time**: 过期时间（可选）
    - **max_views**: 最大查看次数（可选）
    - **access_key**: 访问密钥，空字符串表示禁用（可选）
    """
    admin_key = _get_admin_key_from_header(x_paste_admin_key)

    try:
        PasteService.update_paste(db, paste_id, admin_key, update_data)
        return MessageResponse(message="Paste更新成功")
    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.delete("/{paste_id}", response_model=MessageResponse)
async def delete_paste(
    paste_id: str,
    x_paste_admin_key: str | None = Header(None, alias="X-Paste-Admin-Key"),
    db: Session = Depends(get_db),
):
    """
    删除Paste

    需要在X-Paste-Admin-Key头中提供admin_key
    """
    admin_key = _get_admin_key_from_header(x_paste_admin_key)

    try:
        PasteService.delete_paste(db, paste_id, admin_key)
        return MessageResponse(message="Paste删除成功", timestamp=int(time.time()))
    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None
