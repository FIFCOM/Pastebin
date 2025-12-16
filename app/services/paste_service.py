"""
Paste服务层 - 业务逻辑处理
"""

import base64
import hashlib
import json
import secrets
import string
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.security import (
    bytes_to_str,
    decrypt_with_key,
    encrypt_with_key,
    generate_encryption_key,
    hash_password,
    key_to_urlsafe_str,
    str_to_bytes,
    urlsafe_str_to_key,
    verify_password,
)
from app.core.time_utils import is_expired
from app.models.paste import File, FileUploadSession, Paste, PasteKey
from app.schemas.paste import (
    FileInfo,
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
    get_expire_datetime,
)
from config.config import settings


class PasteService:
    """Paste服务类"""

    FILE_CHUNK_AAD_PREFIX = "mb:filechunk:v1"

    @staticmethod
    def _upload_session_dir(paste_id: str, upload_id: str) -> Path:
        return Path(settings.data_dir) / "uploads" / "files" / paste_id / upload_id

    @staticmethod
    def _upload_chunk_path(paste_id: str, upload_id: str, index: int) -> Path:
        return PasteService._upload_session_dir(paste_id, upload_id) / "chunks" / f"{index:08d}.part"

    @staticmethod
    def _final_file_path(paste_id: str, file_id: str) -> Path:
        return Path(settings.data_dir) / "files" / paste_id / file_id

    @staticmethod
    def _final_manifest_path(paste_id: str, file_id: str) -> Path:
        return Path(settings.data_dir) / "files" / paste_id / f"{file_id}.manifest.json"

    @staticmethod
    def _file_chunk_aad(paste_id: str, file_id: str, chunk_index: int, total_chunks: int) -> bytes:
        # AAD 约定（前后端需一致）：用于绑定 paste/file/chunk 维度，防乱序/重放/篡改
        return f"{PasteService.FILE_CHUNK_AAD_PREFIX}|paste:{paste_id}|file:{file_id}|i:{chunk_index}|n:{total_chunks}".encode()

    @staticmethod
    def init_file_upload(
        db: Session,
        paste_id: str,
        admin_key: str,
        req: FileUploadInitRequest,
        encryption_key: str | None = None,
    ) -> FileUploadInitResponse:
        """
        初始化分片上传会话（application/octet-stream 分片上传）。

        - upload_id 也是最终 File.id
        - chunk_size 为“明文分片大小”；client 模式下上传的是加密分片（长度=明文分片+28B）
        """
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")

        if not PasteService._verify_admin_key(paste, admin_key):
            raise ValueError("管理密钥错误")

        paste_encryption_mode = str(paste.encryption_mode or "client")  # type: ignore
        request_encryption_mode = (
            str(req.encryption_mode).strip() if req.encryption_mode else None
        )
        encryption_mode = request_encryption_mode or paste_encryption_mode
        if encryption_mode not in ("client", "server"):
            raise ValueError("无效的encryption_mode")
        if paste_encryption_mode != encryption_mode:
            raise ValueError("encryption_mode与Paste不一致")

        max_file_size = int(settings.max_upload_file_size)
        if max_file_size > 0 and req.file_size > max_file_size:
            raise ValueError(f"文件过大，最大允许 {max_file_size} 字节")

        now = datetime.now(UTC)
        active_sessions = (
            db.query(FileUploadSession)
            .filter(FileUploadSession.expire_at > now)
            .count()
        )
        if int(settings.max_concurrent_uploads) > 0 and active_sessions >= int(
            settings.max_concurrent_uploads
        ):
            raise ValueError("当前上传会话过多，请稍后重试")

        requested = int(req.requested_chunk_size or int(settings.max_chunk_size))
        if requested <= 0:
            requested = int(settings.max_chunk_size)
        chunk_size = min(requested, int(settings.max_chunk_size))
        if req.file_size > 0:
            chunk_size = min(chunk_size, int(req.file_size))
        else:
            chunk_size = max(1, chunk_size)

        total_chunks = (int(req.file_size) + chunk_size - 1) // chunk_size
        if total_chunks <= 0:
            total_chunks = 1

        # 生成 upload_id（同时作为最终 file_id）
        import uuid

        upload_id = str(uuid.uuid4())
        # IV 前缀使用 upload_id 派生，确保同一 paste_key 下跨文件/跨会话也不重复
        iv_prefix_b64 = base64.b64encode(
            hashlib.sha256(upload_id.encode("utf-8")).digest()[:8]
        ).decode("ascii")

        file_name_encrypted: str
        if encryption_mode == "server":
            paste_key = PasteService._get_server_key_for_write(
                db, paste_id, encryption_key
            )
            file_name_encrypted = bytes_to_str(
                encrypt_with_key(str(req.file_name).encode("utf-8"), paste_key)
            )
        else:
            # client 模式下约定 file_name 为加密后的 Base64；这里做一次快速校验便于定位错误
            try:
                base64.b64decode(str(req.file_name), validate=True)
            except Exception as e:
                raise ValueError(f"file_name格式错误（需为Base64）: {e}") from None
            file_name_encrypted = str(req.file_name)

        expires_at = now + timedelta(seconds=int(settings.upload_expire_seconds))

        session = FileUploadSession(
            id=upload_id,
            paste_id=paste_id,
            encryption_mode=encryption_mode,
            file_name_encrypted=file_name_encrypted,
            mime_type=str(req.mime_type or "application/octet-stream"),
            file_size=int(req.file_size),
            chunk_size=int(chunk_size),
            total_chunks=int(total_chunks),
            iv_prefix=iv_prefix_b64,
            expire_at=expires_at,
        )
        db.add(session)
        db.commit()

        # 创建上传目录
        chunk_dir = PasteService._upload_session_dir(paste_id, upload_id) / "chunks"
        chunk_dir.mkdir(parents=True, exist_ok=True)

        return FileUploadInitResponse(
            upload_id=upload_id,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            expires_at=expires_at,
            aad_prefix=PasteService.FILE_CHUNK_AAD_PREFIX,
            aad_required=True,
            iv_scheme="prefix8=sha256(upload_id)[:8]; iv=prefix8||chunk_index_u32be",
        )

    @staticmethod
    def get_file_upload_status(
        db: Session, paste_id: str, upload_id: str, admin_key: str
    ) -> FileUploadStatusResponse:
        """获取分片上传状态（用于断点续传）。"""
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

        if is_expired(session.expire_at):  # type: ignore[arg-type]
            PasteService.abort_file_upload(db, paste_id, upload_id, admin_key)
            raise ValueError("上传会话已过期")

        total_chunks = int(session.total_chunks)  # type: ignore
        chunk_size = int(session.chunk_size)  # type: ignore
        file_size = int(session.file_size)  # type: ignore

        chunk_dir = PasteService._upload_session_dir(paste_id, upload_id) / "chunks"
        uploaded: set[int] = set()
        if chunk_dir.exists():
            for p in chunk_dir.glob("*.part"):
                if not p.is_file():
                    continue
                try:
                    idx = int(p.stem, 10)
                except Exception:
                    continue
                if 0 <= idx < total_chunks:
                    uploaded.add(idx)

        uploaded_list = sorted(uploaded)
        next_index = total_chunks
        for i in range(total_chunks):
            if i not in uploaded:
                next_index = i
                break

        return FileUploadStatusResponse(
            upload_id=upload_id,
            encryption_mode=str(session.encryption_mode),
            file_size=file_size,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            expires_at=session.expire_at,  # type: ignore[arg-type]
            uploaded_chunks=uploaded_list,
            uploaded_count=len(uploaded_list),
            next_index=next_index,
            completed=len(uploaded_list) == total_chunks,
        )

    @staticmethod
    def complete_file_upload(
        db: Session,
        paste_id: str,
        upload_id: str,
        admin_key: str,
        req: FileUploadCompleteRequest,
        encryption_key: str | None = None,
    ) -> FileUploadCompleteResponse:
        """完成分片上传：校验分片齐全后组装落盘并创建 File 记录。"""
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

        if is_expired(session.expire_at):  # type: ignore[arg-type]
            PasteService.abort_file_upload(db, paste_id, upload_id, admin_key)
            raise ValueError("上传会话已过期")

        encryption_mode = str(session.encryption_mode)
        chunk_size = int(session.chunk_size)  # type: ignore
        total_chunks = int(session.total_chunks)  # type: ignore
        plain_size = int(session.file_size)  # type: ignore

        upload_dir = PasteService._upload_session_dir(paste_id, upload_id)
        assembled_tmp = upload_dir / "assembled.tmp"

        sha256_encrypted = hashlib.sha256()
        sha256_plain = hashlib.sha256()
        chunk_hashes = req.chunk_hashes_sha256
        if chunk_hashes is not None and len(chunk_hashes) != total_chunks:
            raise ValueError("chunk_hashes_sha256数量与total_chunks不一致")

        final_file_dir = Path(settings.data_dir) / "files" / paste_id
        final_file_dir.mkdir(parents=True, exist_ok=True)
        final_path = PasteService._final_file_path(paste_id, upload_id)
        if final_path.exists():
            raise ValueError("目标文件已存在")

        if encryption_mode == "server":
            paste_key = PasteService._get_server_key_for_write(
                db, paste_id, encryption_key
            )
            iv_prefix_b64 = str(session.iv_prefix) if session.iv_prefix else None  # type: ignore
            iv_prefix = base64.b64decode(iv_prefix_b64) if iv_prefix_b64 else None
            if iv_prefix is None or len(iv_prefix) != 8:
                raise ValueError("服务端上传会话IV前缀无效")

            with open(assembled_tmp, "wb") as out:
                for index in range(total_chunks):
                    chunk_path = PasteService._upload_chunk_path(paste_id, upload_id, index)
                    if not chunk_path.exists():
                        raise ValueError(f"缺少分片: {index}")
                    chunk_bytes = chunk_path.read_bytes()

                    expected_plain = chunk_size if index < total_chunks - 1 else plain_size - chunk_size * (total_chunks - 1)
                    if expected_plain < 0:
                        expected_plain = 0
                    if len(chunk_bytes) != expected_plain:
                        raise ValueError(f"分片大小不匹配: index={index}")

                    if chunk_hashes is not None:
                        chunk_digest = hashlib.sha256(chunk_bytes).hexdigest()
                        if chunk_digest != chunk_hashes[index]:
                            raise ValueError(f"分片hash校验失败: index={index}")

                    sha256_plain.update(chunk_bytes)

                    # deterministic nonce: prefix(8B) + chunk_index(4B, big-endian)
                    iv = iv_prefix + int(index).to_bytes(4, "big", signed=False)
                    aad = PasteService._file_chunk_aad(paste_id, upload_id, index, total_chunks)
                    encrypted_chunk = encrypt_with_key(chunk_bytes, paste_key, aad=aad, iv=iv)
                    out.write(encrypted_chunk)
                    sha256_encrypted.update(encrypted_chunk)
        else:
            # client: 分片已经加密；要求IV为 deterministic: prefix(8B from upload_id sha256) + chunk_index(4B)
            iv_prefix_b64 = str(session.iv_prefix) if session.iv_prefix else None  # type: ignore
            iv_prefix = base64.b64decode(iv_prefix_b64) if iv_prefix_b64 else None
            if iv_prefix is None or len(iv_prefix) != 8:
                raise ValueError("上传会话IV前缀无效")

            seen_ivs: set[bytes] = set()
            with open(assembled_tmp, "wb") as out:
                for index in range(total_chunks):
                    chunk_path = PasteService._upload_chunk_path(paste_id, upload_id, index)
                    if not chunk_path.exists():
                        raise ValueError(f"缺少分片: {index}")
                    chunk_bytes = chunk_path.read_bytes()

                    expected_plain = chunk_size if index < total_chunks - 1 else plain_size - chunk_size * (total_chunks - 1)
                    if expected_plain < 0:
                        expected_plain = 0
                    expected_encrypted = expected_plain + 12 + 16
                    if len(chunk_bytes) != expected_encrypted:
                        raise ValueError(f"分片大小不匹配: index={index}")
                    iv = bytes(chunk_bytes[:12])
                    expected_iv = iv_prefix + int(index).to_bytes(4, "big", signed=False)
                    if iv != expected_iv:
                        raise ValueError(f"分片IV不匹配: index={index}")
                    if iv in seen_ivs:
                        raise ValueError("检测到重复IV（同一key下必须保证IV不重复）")
                    seen_ivs.add(iv)

                    if chunk_hashes is not None:
                        chunk_digest = hashlib.sha256(chunk_bytes).hexdigest()
                        if chunk_digest != chunk_hashes[index]:
                            raise ValueError(f"分片hash校验失败: index={index}")

                    out.write(chunk_bytes)
                    sha256_encrypted.update(chunk_bytes)

        encrypted_size = assembled_tmp.stat().st_size

        # 可选校验原始文件 hash（仅 server 模式下可重算；client 模式下无法校验）
        if req.checksum_sha256 and encryption_mode == "server":
            if sha256_plain.hexdigest() != req.checksum_sha256:
                raise ValueError("checksum_sha256校验失败")

        manifest_path = PasteService._final_manifest_path(paste_id, upload_id)
        try:
            # 原子移动到最终路径
            assembled_tmp.replace(final_path)

            # 写入manifest（避免DB迁移；下载/解密时可用）
            manifest = {
                "version": 1,
                "paste_id": paste_id,
                "file_id": upload_id,
                "encryption_mode": encryption_mode,
                "plain_size": plain_size,
                "chunk_size": chunk_size,
                "total_chunks": total_chunks,
                "chunk_overhead_bytes": 28,
                "chunk_format": "aes-gcm-iv12-ciphertext-tag16",
                "aad_format": f"{PasteService.FILE_CHUNK_AAD_PREFIX}|paste:{{paste_id}}|file:{{file_id}}|i:{{chunk_index}}|n:{{total_chunks}}",
                "aad_required": True,
                "iv_scheme": "prefix8+index4be",
                "iv_prefix": str(session.iv_prefix),
            }
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )

            # 创建文件记录
            file_record = File(
                id=upload_id,
                paste_id=paste_id,
                file_name_encrypted=str(session.file_name_encrypted),  # type: ignore
                mime_type=str(session.mime_type),  # type: ignore
                file_size=int(encrypted_size),
                storage_path=str(final_path.relative_to(Path(settings.data_dir))),
                checksum=sha256_encrypted.hexdigest(),
            )
            db.add(file_record)

            # 如果是已发布状态，更新为编辑状态
            if str(paste.status) == "published":  # type: ignore
                paste.status = "edited"  # type: ignore
                paste.updated_at = datetime.now(UTC)  # type: ignore

            # 删除上传会话并清理临时文件
            db.delete(session)
            db.commit()
        except Exception:
            db.rollback()
            try:
                if final_path.exists():
                    final_path.unlink()
                if manifest_path.exists():
                    manifest_path.unlink()
            except Exception:
                pass
            raise
        try:
            if upload_dir.exists():
                for p in sorted(upload_dir.rglob("*"), reverse=True):
                    if p.is_file():
                        p.unlink(missing_ok=True)
                    else:
                        p.rmdir()
                upload_dir.rmdir()
        except Exception:
            pass

        return FileUploadCompleteResponse(file_id=upload_id)

    @staticmethod
    def abort_file_upload(db: Session, paste_id: str, upload_id: str, admin_key: str) -> None:
        """取消分片上传并清理临时数据。"""
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
        if session:
            db.delete(session)
            db.commit()

        upload_dir = PasteService._upload_session_dir(paste_id, upload_id)
        try:
            if upload_dir.exists():
                for p in sorted(upload_dir.rglob("*"), reverse=True):
                    if p.is_file():
                        p.unlink(missing_ok=True)
                    else:
                        p.rmdir()
                upload_dir.rmdir()
        except Exception:
            pass
    @staticmethod
    def _get_server_key_for_write(
        db: Session, paste_id: str, encryption_key: str | None
    ) -> bytes:
        """
        获取用于服务端加密写入的密钥。

        - 草稿阶段优先使用数据库中临时保存的 PasteKey
        - 发布后（PasteKey 已删除）需要由客户端在请求中携带 encryption_key
        """
        paste_key_record = (
            db.query(PasteKey).filter(PasteKey.paste_id == paste_id).first()
        )
        if paste_key_record:
            return urlsafe_str_to_key(str(paste_key_record.paste_key))  # type: ignore

        if not encryption_key or str(encryption_key).strip() == "":
            raise ValueError("服务端加密模式缺少encryption_key")

        try:
            return urlsafe_str_to_key(str(encryption_key))
        except Exception as e:
            raise ValueError(f"encryption_key格式错误: {e}") from None

    @staticmethod
    def _generate_paste_id() -> str:
        """生成8位随机Paste ID"""
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(8))

    @staticmethod
    def _generate_admin_key() -> str:
        """生成16位随机管理密钥"""
        return secrets.token_urlsafe(12)  # 生成16字符的URL安全字符串

    @staticmethod
    def _generate_paste_key() -> str:
        """生成Paste加密密钥（URL-safe格式）"""
        return key_to_urlsafe_str(generate_encryption_key())

    @staticmethod
    def _verify_admin_key(paste: Paste, admin_key: str) -> bool:
        """验证管理密钥"""
        return str(paste.admin_key) == admin_key  # type: ignore

    @staticmethod
    def _verify_access_key(paste: Paste, access_key: str | None) -> bool:
        """验证访问密钥"""
        if not paste.access_key_hash:  # type: ignore
            return True  # 没有设置访问密钥
        if not access_key:
            return False  # 需要访问密钥但未提供
        return verify_password(access_key, str(paste.access_key_hash))  # type: ignore

    @staticmethod
    def _save_content_to_file(paste_id: str, content: str) -> str:
        """将内容保存到文件并返回路径"""
        content_dir = Path(settings.data_dir) / "content"
        content_dir.mkdir(parents=True, exist_ok=True)

        file_path = content_dir / f"{paste_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path.relative_to(Path(settings.data_dir)))

    @staticmethod
    def _read_content_from_file(content_path: str) -> str:
        """从文件读取内容"""
        full_path = Path(settings.data_dir) / content_path
        if not full_path.exists():
            raise FileNotFoundError(f"内容文件不存在: {content_path}")

        with open(full_path, encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _save_file_to_storage(paste_id: str, file_id: str, file_data: bytes) -> str:
        """将文件保存到存储并返回路径"""
        file_dir = Path(settings.data_dir) / "files" / paste_id
        file_dir.mkdir(parents=True, exist_ok=True)

        file_path = file_dir / file_id
        with open(file_path, "wb") as f:
            f.write(file_data)

        return str(file_path.relative_to(Path(settings.data_dir)))

    @staticmethod
    def create_paste(
        db: Session, paste_data: PasteCreateRequest
    ) -> PasteCreateResponse:
        """
        创建新Paste（草稿状态）

        Args:
            db: 数据库会话
            paste_data: Paste创建数据

        Returns:
            创建的Paste信息

        Raises:
            ValueError: 当生成ID冲突时
        """
        # 生成唯一的Paste ID
        max_attempts = 10
        for _ in range(max_attempts):
            paste_id = PasteService._generate_paste_id()
            if not db.query(Paste).filter(Paste.id == paste_id).first():
                break
        else:
            raise ValueError("无法生成唯一的Paste ID")

        # 生成管理密钥
        admin_key = PasteService._generate_admin_key()

        # 设置草稿24小时过期
        expire_at = datetime.now(UTC) + timedelta(hours=24)

        # 创建Paste记录
        paste = Paste(
            id=paste_id,
            status="draft",
            encryption_mode=paste_data.encryption_mode,
            admin_key=admin_key,
            expire_at=expire_at,
        )

        # 如果是服务端加密模式，生成并保存加密密钥
        if paste_data.encryption_mode == "server":
            paste_key = PasteService._generate_paste_key()
            paste_key_record = PasteKey(paste_id=paste_id, paste_key=paste_key)
            db.add(paste_key_record)

        db.add(paste)
        db.commit()
        db.refresh(paste)

        return PasteCreateResponse(
            paste_id=paste_id,
            admin_key=admin_key,
            expires_at=expire_at,
            timestamp=int(datetime.now(UTC).timestamp()),
        )

    @staticmethod
    def update_paste_content(
        db: Session,
        paste_id: str,
        admin_key: str,
        content_data: PasteContentUpdateRequest,
        encryption_key: str | None = None,
    ) -> None:
        """
        更新Paste内容

        Args:
            db: 数据库会话
            paste_id: Paste ID
            admin_key: 管理密钥
            content_data: 内容更新数据

        Raises:
            ValueError: 当Paste不存在或权限验证失败时
        """
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")

        if not PasteService._verify_admin_key(paste, admin_key):
            raise ValueError("管理密钥错误")

        # 根据加密模式处理内容
        if str(paste.encryption_mode) == "client":  # type: ignore
            if not content_data.encrypted_content:
                raise ValueError("客户端加密模式需要提供encrypted_content")
            content_to_save = content_data.encrypted_content
        else:  # server
            if not content_data.content:
                raise ValueError("服务端加密模式需要提供content")

            # 使用服务端密钥加密内容（发布后由客户端携带encryption_key）
            paste_key = PasteService._get_server_key_for_write(
                db, paste_id, encryption_key
            )
            encrypted_content = encrypt_with_key(
                content_data.content.encode(), paste_key
            )
            content_to_save = bytes_to_str(encrypted_content)

        # 保存内容到文件
        content_path = PasteService._save_content_to_file(paste_id, content_to_save)
        paste.content_path = content_path  # type: ignore

        # 如果是已发布状态，更新为编辑状态
        if str(paste.status) == "published":  # type: ignore
            paste.status = "edited"  # type: ignore

        paste.updated_at = datetime.now(UTC)  # type: ignore
        db.commit()

    @staticmethod
    @staticmethod
    def delete_file(db: Session, paste_id: str, file_id: str, admin_key: str) -> None:
        """
        删除文件

        Args:
            db: 数据库会话
            paste_id: Paste ID
            file_id: 文件ID
            admin_key: 管理密钥

        Raises:
            ValueError: 当Paste或文件不存在，或权限验证失败时
        """
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")

        if not PasteService._verify_admin_key(paste, admin_key):
            raise ValueError("管理密钥错误")

        file_record = (
            db.query(File).filter(File.id == file_id, File.paste_id == paste_id).first()
        )
        if not file_record:
            raise ValueError("文件不存在")

        # 删除物理文件
        try:
            file_path = Path(settings.data_dir) / str(file_record.storage_path)  # type: ignore
            if file_path.exists():
                file_path.unlink()

            manifest_path = PasteService._final_manifest_path(paste_id, file_id)
            if manifest_path.exists():
                manifest_path.unlink()
        except Exception:
            pass  # 忽略文件删除错误

        # 删除数据库记录
        db.delete(file_record)
        db.commit()

    @staticmethod
    def publish_paste(
        db: Session, paste_id: str, admin_key: str, publish_data: PastePublishRequest
    ) -> PastePublishResponse:
        """
        发布Paste

        Args:
            db: 数据库会话
            paste_id: Paste ID
            admin_key: 管理密钥
            publish_data: 发布数据

        Returns:
            发布响应

        Raises:
            ValueError: 当验证失败时
        """
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")

        if not PasteService._verify_admin_key(paste, admin_key):
            raise ValueError("管理密钥错误")

        if str(paste.status) != "draft":  # type: ignore
            raise ValueError("只能发布草稿状态的Paste")

        # 验证必要字段
        if not paste.content_path:  # type: ignore
            raise ValueError("Paste内容不能为空")

        settings_data = publish_data.settings

        # 设置标题
        if not settings_data.title or not settings_data.title.strip():
            raise ValueError("Paste标题不能为空")
        paste.title = settings_data.title  # type: ignore

        # 设置Paste类型
        paste.type = settings_data.type  # type: ignore

        # 设置过期时间
        expire_at = get_expire_datetime(settings_data.expire_time)
        paste.expire_at = expire_at  # type: ignore

        # 设置最大查看次数
        paste.max_views = settings_data.max_views  # type: ignore

        # 设置访问密钥
        if settings_data.access_key:
            paste.access_key_hash = hash_password(settings_data.access_key)  # type: ignore

        # 更新状态
        paste.status = "published"  # type: ignore
        paste.published_at = datetime.now(UTC)  # type: ignore
        paste.updated_at = datetime.now(UTC)  # type: ignore

        db.commit()

        # 准备响应
        encryption_key = None

        # 如果是服务端加密模式，返回加密密钥并删除临时存储
        if str(paste.encryption_mode) == "server":  # type: ignore
            paste_key_record = (
                db.query(PasteKey).filter(PasteKey.paste_id == paste_id).first()
            )
            if paste_key_record:
                encryption_key = str(paste_key_record.paste_key)  # type: ignore
                # 删除临时存储的密钥（发布后返回给用户）
                db.delete(paste_key_record)
                db.commit()

        return PastePublishResponse(
            paste_id=paste_id,
            admin_key=admin_key,
            encryption_key=encryption_key,
            timestamp=int(datetime.now(UTC).timestamp()),
        )

    @staticmethod
    def get_paste_info(
        db: Session, paste_id: str, access_key: str | None = None
    ) -> PasteResponse:
        """
        获取Paste信息

        Args:
            db: 数据库会话
            paste_id: Paste ID
            access_key: 访问密钥（可选）

        Returns:
            Paste信息

        Raises:
            ValueError: 当Paste不存在或权限验证失败时
        """
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")

        if str(paste.status) == "draft":  # type: ignore
            raise ValueError("草稿状态的Paste不可访问")

        # 验证访问权限
        if not PasteService._verify_access_key(paste, access_key):
            raise ValueError("访问密钥错误")

        # 检查是否过期（兼容 SQLite 返回的 naive datetime）
        if is_expired(paste.expire_at):  # type: ignore[arg-type]
            raise ValueError("Paste已过期")

        return PasteResponse(
            title=str(paste.title) if paste.title else None,  # type: ignore
            type=str(paste.type) if paste.type else "txt",  # type: ignore
            status=str(paste.status),  # type: ignore
            published_at=paste.published_at,  # type: ignore
            updated_at=paste.updated_at,  # type: ignore
            expire_at=paste.expire_at,  # type: ignore
            view_count=int(paste.view_count or 0),  # type: ignore
            max_views=int(paste.max_views or -1),  # type: ignore
        )

    @staticmethod
    def get_paste_content(
        db: Session,
        paste_id: str,
        access_key: str | None = None,
        encryption_key: str | None = None,
    ) -> PasteContentResponse:
        """
        获取Paste内容

        Args:
            db: 数据库会话
            paste_id: Paste ID
            access_key: 访问密钥（可选）
            encryption_key: 解密密钥（可选）

        Returns:
            Paste内容

        Raises:
            ValueError: 当权限验证失败时
        """
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")

        if str(paste.status) == "draft":  # type: ignore
            raise ValueError("草稿状态的Paste不可访问")

        # 验证访问权限
        if not PasteService._verify_access_key(paste, access_key):
            raise ValueError("访问密钥错误")

        # 检查是否过期（兼容 SQLite 返回的 naive datetime）
        if is_expired(paste.expire_at):  # type: ignore[arg-type]
            raise ValueError("Paste已过期")

        content_path = paste.content_path  # type: ignore
        if content_path is None or str(content_path).strip() == "":
            raise ValueError("Paste内容为空")

        # 检查查看次数限制并增加计数
        paste_max_views = int(paste.max_views or -1)  # type: ignore
        paste_view_count = int(paste.view_count or 0)  # type: ignore
        if paste_max_views > 0 and paste_view_count >= paste_max_views:
            raise ValueError("Paste已达到最大查看次数")

        # 增加查看次数
        paste.view_count = paste_view_count + 1  # type: ignore
        db.commit()

        # 读取内容
        encrypted_content = PasteService._read_content_from_file(str(content_path))

        response = PasteContentResponse()

        # 如果提供了解密密钥，尝试解密
        if encryption_key:
            try:
                key_bytes = urlsafe_str_to_key(encryption_key)
                content_bytes = str_to_bytes(encrypted_content)
                decrypted_bytes = decrypt_with_key(content_bytes, key_bytes)
                response.content = decrypted_bytes.decode()
            except Exception:
                # 解密失败，抛出异常
                raise ValueError("解密密钥错误") from None
        else:
            response.encrypted_content = encrypted_content

        # 获取文件列表（与内容接口一起返回，便于一次性加载）
        files = db.query(File).filter(File.paste_id == paste_id).all()
        if files:
            def _manifest_fields(
                file_id: str,
            ) -> int | None:
                try:
                    manifest_path = PasteService._final_manifest_path(paste_id, file_id)
                    if not manifest_path.exists():
                        return None
                    data = json.loads(manifest_path.read_text(encoding="utf-8"))
                    plain_size = data.get("plain_size")
                    return int(plain_size) if plain_size is not None else None
                except Exception:
                    return None

            file_infos: list[FileInfo] = []
            for f in files:
                file_id = str(f.id)  # type: ignore
                plain_size = _manifest_fields(file_id)
                file_infos.append(
                    FileInfo(
                        id=file_id,
                        size=int(f.file_size),  # type: ignore
                        encrypted_name=str(f.file_name_encrypted),  # type: ignore
                        url=f"/api/pastes/{paste_id}/files/{file_id}",
                        plain_size=plain_size,
                    )
                )

            response.files = file_infos

        return response

    @staticmethod
    def update_paste(
        db: Session, paste_id: str, admin_key: str, update_data: PasteUpdateRequest
    ) -> None:
        """
        更新Paste设置

        Args:
            db: 数据库会话
            paste_id: Paste ID
            admin_key: 管理密钥
            update_data: 更新数据

        Raises:
            ValueError: 当验证失败时
        """
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")

        if not PasteService._verify_admin_key(paste, admin_key):
            raise ValueError("管理密钥错误")

        # 更新字段
        if update_data.title is not None:
            paste.title = update_data.title  # type: ignore

        if update_data.type is not None:
            paste.type = update_data.type  # type: ignore

        if update_data.expire_time is not None:
            paste.expire_at = get_expire_datetime(update_data.expire_time)  # type: ignore

        if update_data.max_views is not None:
            paste.max_views = update_data.max_views  # type: ignore

        if update_data.access_key is not None:
            if update_data.access_key == "":
                paste.access_key_hash = None  # type: ignore # 禁用访问密钥
            else:
                paste.access_key_hash = hash_password(update_data.access_key)  # type: ignore

        # 如果是已发布状态，更新为编辑状态
        if str(paste.status) == "published":  # type: ignore
            paste.status = "edited"  # type: ignore

        paste.updated_at = datetime.now(UTC)  # type: ignore
        db.commit()

    @staticmethod
    def delete_paste(db: Session, paste_id: str, admin_key: str) -> None:
        """
        删除Paste

        Args:
            db: 数据库会话
            paste_id: Paste ID
            admin_key: 管理密钥

        Raises:
            ValueError: 当验证失败时
        """
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")

        if not PasteService._verify_admin_key(paste, admin_key):
            raise ValueError("管理密钥错误")

        # 删除相关文件
        files = db.query(File).filter(File.paste_id == paste_id).all()
        for file_record in files:
            try:
                file_path = Path(settings.data_dir) / str(file_record.storage_path)  # type: ignore
                if file_path.exists():
                    file_path.unlink()
                manifest_path = PasteService._final_manifest_path(
                    paste_id, str(file_record.id)  # type: ignore
                )
                if manifest_path.exists():
                    manifest_path.unlink()
            except Exception:
                pass  # 忽略文件删除错误

        # 删除内容文件
        content_path = paste.content_path  # type: ignore
        if content_path is not None and str(content_path).strip() != "":
            try:
                full_content_path = Path(settings.data_dir) / str(content_path)
                if full_content_path.exists():
                    full_content_path.unlink()
            except Exception:
                pass

        # 删除Paste记录（会级联删除相关记录）
        db.delete(paste)
        db.commit()
