"""
Paste控制器 - REST API路由
"""

import io
import time
from datetime import UTC, datetime
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

from app.core.database import get_db
from app.schemas.common import MessageResponse
from app.schemas.paste import (
    FileUploadCompleteRequest,
    FileUploadCompleteResponse,
    FileUploadInitRequest,
    FileUploadInitResponse,
    PasteContentResponse,
    PasteContentUpdateRequest,
    PasteCreateRequest,
    PasteCreateResponse,
    PastePublishRequest,
    PastePublishResponse,
    PasteResponse,
    PasteUpdateRequest,
)
from app.services.paste_service import PasteService

# 创建路由器
router = APIRouter(prefix="/api/pastes", tags=["Paste"])


def _build_content_disposition(filename: str) -> str:
    """
    构造安全的 Content-Disposition 头，避免 CRLF 注入，并尽量兼容非 ASCII 文件名。

    返回格式示例：
    attachment; filename="fallback.txt"; filename*=UTF-8''%E4%B8%AD%E6%96%87.txt
    """
    from pathlib import Path

    # 只保留文件名，避免路径穿透/分隔符
    name = str(Path(filename).name)

    # 移除可能造成响应头注入的字符
    name = name.replace("\r", "_").replace("\n", "_").replace("\x00", "_")

    # 替换不可见控制字符
    name = "".join((ch if ord(ch) >= 32 and ord(ch) != 127 else "_") for ch in name)

    # 避免破坏 quoted-string
    name = name.replace("\\", "_").replace('"', "'").strip()
    if not name:
        name = "encrypted_file"

    # 限制长度，避免异常超长 header
    name = name[:200]

    ascii_fallback = name.encode("ascii", "ignore").decode("ascii").strip()
    if not ascii_fallback:
        ascii_fallback = "encrypted_file"
    ascii_fallback = ascii_fallback.replace("\\", "_").replace('"', "'")[:200]

    # RFC 5987 (filename*)：UTF-8 + percent-encoding
    encoded = quote(name, safe="")
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'


def _iter_file(path, chunk_size: int = 1024 * 1024):
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def _get_admin_key_from_header(authorization: str | None) -> str:
    """从Authorization头中提取admin_key"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少Authorization头",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的Authorization格式",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return authorization[7:]  # 去掉 "Bearer " 前缀


@router.post(
    "", response_model=PasteCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_paste(paste_data: PasteCreateRequest, db: Session = Depends(get_db)):
    """
    创建新Paste（草稿状态）

    - **encryption_mode**: 加密模式，client（客户端加密）或server（服务端加密）
    """
    try:
        return PasteService.create_paste(db, paste_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.post("/{paste_id}/content", response_model=MessageResponse)
async def update_paste_content(
    paste_id: str,
    content_data: PasteContentUpdateRequest,
    authorization: str | None = Header(None),
    encryption_key: str | None = Header(
        None, alias="X-Encryption-Key", description="服务端加密模式下用于加密写入的密钥"
    ),
    db: Session = Depends(get_db),
):
    """
    上传/更新Paste内容

    需要在Authorization头中提供admin_key: Bearer {admin_key}

    - **encrypted_content**: Base64编码的加密内容（客户端加密模式）
    - **content**: 明文内容（服务端加密模式）
    """
    admin_key = _get_admin_key_from_header(authorization)

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
    authorization: str | None = Header(None),
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
    admin_key = _get_admin_key_from_header(authorization)
    try:
        return PasteService.init_file_upload(
            db, paste_id, admin_key, body, encryption_key=encryption_key
        )
    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from None
        elif "不存在" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.put("/{paste_id}/files/{upload_id}/chunk/{index}", response_model=MessageResponse)
async def upload_file_chunk(
    paste_id: str,
    upload_id: str,
    index: int,
    request: Request,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    上传单个分片（二进制）

    Content-Type: application/octet-stream
    """
    admin_key = _get_admin_key_from_header(authorization)
    try:
        from datetime import UTC, datetime

        from app.models.paste import FileUploadSession, Paste

        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")
        if not PasteService._verify_admin_key(paste, admin_key):
            raise ValueError("管理密钥错误")

        session = (
            db.query(FileUploadSession)
            .filter(FileUploadSession.id == upload_id, FileUploadSession.paste_id == paste_id)
            .first()
        )
        if not session:
            raise ValueError("上传会话不存在或已过期")

        now = datetime.now(UTC)
        if session.expire_at < now:  # type: ignore
            PasteService.abort_file_upload(db, paste_id, upload_id, admin_key)
            raise ValueError("上传会话已过期")

        total_chunks = int(session.total_chunks)  # type: ignore
        chunk_size = int(session.chunk_size)  # type: ignore
        plain_size = int(session.file_size)  # type: ignore

        if index < 0 or index >= total_chunks:
            raise ValueError("分片索引越界")

        expected_plain = chunk_size if index < total_chunks - 1 else plain_size - chunk_size * (total_chunks - 1)
        if expected_plain < 0:
            expected_plain = 0

        encryption_mode = str(session.encryption_mode)
        expected_len = expected_plain if encryption_mode == "server" else expected_plain + 12 + 16

        expected_iv: bytes | None = None
        if encryption_mode == "client":
            import base64

            iv_prefix_b64 = str(session.iv_prefix) if session.iv_prefix is not None else ""
            try:
                iv_prefix = base64.b64decode(iv_prefix_b64, validate=True)
            except Exception:
                raise ValueError("上传会话IV前缀无效") from None
            if len(iv_prefix) != 8:
                raise ValueError("上传会话IV前缀无效")
            expected_iv = iv_prefix + int(index).to_bytes(4, "big", signed=False)

        # 流式写入，避免一次性读入内存
        chunk_path = PasteService._upload_chunk_path(paste_id, upload_id, index)
        chunk_path.parent.mkdir(parents=True, exist_ok=True)
        if chunk_path.exists():
            raise ValueError("分片已存在")

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
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from None
        elif "不存在" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
        elif "过期" in str(e):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(e)) from None
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
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
    authorization: str | None = Header(None),
    encryption_key: str | None = Header(
        None, alias="X-Encryption-Key", description="服务端加密模式下用于加密写入的密钥"
    ),
    db: Session = Depends(get_db),
):
    """
    完成分片上传并落盘
    """
    admin_key = _get_admin_key_from_header(authorization)
    try:
        return PasteService.complete_file_upload(
            db, paste_id, upload_id, admin_key, body, encryption_key=encryption_key
        )
    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from None
        elif "不存在" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
        elif "过期" in str(e):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(e)) from None
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.post("/{paste_id}/files/{upload_id}/abort", response_model=MessageResponse)
async def abort_file_upload(
    paste_id: str,
    upload_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    取消分片上传并清理临时数据
    """
    admin_key = _get_admin_key_from_header(authorization)
    try:
        PasteService.abort_file_upload(db, paste_id, upload_id, admin_key)
        return MessageResponse(message="上传已取消", timestamp=int(time.time()))
    except ValueError as e:
        if "权限" in str(e) or "密钥" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from None
        elif "不存在" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.delete("/{paste_id}/files/{file_id}", response_model=MessageResponse)
async def delete_file(
    paste_id: str,
    file_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    删除文件

    需要在Authorization头中提供admin_key: Bearer {admin_key}
    """
    admin_key = _get_admin_key_from_header(authorization)

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
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    发布Paste

    需要在Authorization头中提供admin_key: Bearer {admin_key}

    - **expire_time**: 过期时间（7d, 30d, 1y, never）
    - **max_views**: 最大查看次数（1表示阅后即焚，-1表示无限制）
    - **access_key**: 访问密钥（可选）
    """
    admin_key = _get_admin_key_from_header(authorization)

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
    db: Session = Depends(get_db),
):
    """
    获取Paste信息

    - **access_key**: 访问密钥（如果Paste设置了访问密钥则需要提供）
    """
    try:
        return PasteService.get_paste_info(db, paste_id, access_key)
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
    db: Session = Depends(get_db),
):
    """
    获取Paste内容

    - **access_key**: 访问密钥（如果Paste设置了访问密钥则需要提供）
    - **encryption_key**: 解密密钥（可选，如果提供且正确则返回解密后的内容）
    """
    try:
        return PasteService.get_paste_content(db, paste_id, access_key, encryption_key)
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


@router.get("/{paste_id}/files/{file_id}")
async def get_file(
    paste_id: str,
    file_id: str,
    access_key: str | None = Query(None, description="访问密钥（可选）"),
    encryption_key: str | None = Query(None, description="解密密钥（可选）"),
    db: Session = Depends(get_db),
):
    """
    获取文件

    - **access_key**: 访问密钥（如果Paste设置了访问密钥则需要提供）
    - **encryption_key**: 解密密钥（可选，如果提供且正确则解密文件名和内容）

    返回文件流，Content-Disposition: attachment; filename="filename"
    """
    try:
        from app.models.paste import File, Paste
        from config.config import settings

        # 检查 Paste 状态/访问密钥/过期/阅后即焚
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste or str(paste.status) == "draft":  # type: ignore
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Paste不存在或不可访问"
            )

        if not PasteService._verify_access_key(paste, access_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="访问密钥错误"
            )

        paste_expire_at: datetime | None = cast(datetime | None, paste.expire_at)
        if paste_expire_at is not None and datetime.now(UTC) > paste_expire_at:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="Paste已过期"
            )

        paste_max_views = int(paste.max_views or -1)  # type: ignore
        paste_view_count = int(paste.view_count or 0)  # type: ignore
        if paste_max_views > 0 and paste_view_count >= paste_max_views:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="Paste已达到最大查看次数"
            )

        # 获取文件记录
        file_record = (
            db.query(File)
            .filter(File.id == file_id, File.paste_id == paste_id)
            .first()
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
        filename = "encrypted_file"

        key_bytes: bytes | None = None
        if encryption_key:
            try:
                from app.core.security import (
                    decrypt_with_key,
                    str_to_bytes,
                    urlsafe_str_to_key,
                )

                key_bytes = urlsafe_str_to_key(encryption_key)
                encrypted_name_bytes = str_to_bytes(encrypted_filename)
                decrypted_name_bytes = decrypt_with_key(encrypted_name_bytes, key_bytes)
                filename = decrypted_name_bytes.decode(errors="replace")
            except Exception:
                key_bytes = None

        media_type = str(file_record.mime_type) or "application/octet-stream"  # type: ignore
        content_disposition = _build_content_disposition(filename)

        # 若提供了正确的解密密钥：尽可能解密后返回
        if key_bytes is not None:
            try:
                from app.core.security import decrypt_with_key

                # 分片上传：manifest 存在时可按chunk流式解密，避免一次性读入内存
                manifest_path = (
                    Path(settings.data_dir) / "files" / paste_id / f"{file_id}.manifest.json"
                )
                if manifest_path.exists():
                    import json

                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    chunk_size = int(manifest.get("chunk_size"))
                    total_chunks = int(manifest.get("total_chunks"))
                    plain_size = int(manifest.get("plain_size"))
                    aad_required = bool(manifest.get("aad_required", True))

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
                                if len(iv) != 12 or len(ciphertext) != expected_plain + 16:
                                    raise ValueError("文件分片格式错误")

                                encrypted_chunk = iv + ciphertext
                                aad = PasteService._file_chunk_aad(
                                    paste_id, file_id, idx, total_chunks
                                )
                                if aad_required:
                                    yield decrypt_with_key(encrypted_chunk, key_bytes, aad=aad)
                                else:
                                    yield decrypt_with_key(encrypted_chunk, key_bytes, aad=None)

                    return StreamingResponse(
                        _iter_decrypted_chunks(),
                        media_type=media_type,
                        headers={
                            "Content-Disposition": content_disposition,
                            "Content-Length": str(plain_size),
                        },
                    )

                # 非分片：整体解密（AES-GCM需整体解密，存在内存开销）
                file_content = file_path.read_bytes()
                file_content = decrypt_with_key(file_content, key_bytes)
                return StreamingResponse(
                    io.BytesIO(file_content),
                    media_type=media_type,
                    headers={
                        "Content-Disposition": content_disposition,
                        "Content-Length": str(len(file_content)),
                    },
                )
            except Exception:
                # 解密失败，回退为返回原始加密内容（不强制把错误暴露给客户端）
                pass

        # 未提供/解密失败：直接流式返回原始文件，避免一次性读入内存
        file_size = file_path.stat().st_size
        return StreamingResponse(
            _iter_file(file_path),
            media_type=media_type,
            headers={
                "Content-Disposition": content_disposition,
                "Content-Length": str(file_size),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件读取失败: {str(e)}",
        ) from None


@router.put("/{paste_id}", response_model=MessageResponse)
async def update_paste(
    paste_id: str,
    update_data: PasteUpdateRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    更新Paste设置

    需要在Authorization头中提供admin_key: Bearer {admin_key}

    - **title**: 新标题（可选）
    - **type**: Paste类型：txt或md（可选）
    - **expire_time**: 过期时间（可选）
    - **max_views**: 最大查看次数（可选）
    - **access_key**: 访问密钥，空字符串表示禁用（可选）
    """
    admin_key = _get_admin_key_from_header(authorization)

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
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    删除Paste

    需要在Authorization头中提供admin_key: Bearer {admin_key}
    """
    admin_key = _get_admin_key_from_header(authorization)

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
