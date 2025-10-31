"""
Paste服务层 - 业务逻辑处理
"""

import hashlib
import secrets
import string
from datetime import datetime, timedelta
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
from app.models.paste import File, Paste, PasteKey
from app.schemas.paste import (
    FileInfo,
    FileUploadRequest,
    FileUploadResponse,
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
        expire_at = datetime.utcnow() + timedelta(hours=24)

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
            paste_id=paste_id, admin_key=admin_key, expires_at=expire_at
        )

    @staticmethod
    def update_paste_content(
        db: Session,
        paste_id: str,
        admin_key: str,
        content_data: PasteContentUpdateRequest,
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

            # 获取服务端密钥并加密内容
            paste_key_record = (
                db.query(PasteKey).filter(PasteKey.paste_id == paste_id).first()
            )
            if not paste_key_record:
                raise ValueError("服务端加密密钥不存在")

            # 使用服务端密钥加密内容
            paste_key = urlsafe_str_to_key(str(paste_key_record.paste_key))  # type: ignore
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

        paste.updated_at = datetime.utcnow()  # type: ignore
        db.commit()

    @staticmethod
    def upload_file(
        db: Session, paste_id: str, admin_key: str, file_data: FileUploadRequest
    ) -> FileUploadResponse:
        """
        上传文件

        Args:
            db: 数据库会话
            paste_id: Paste ID
            admin_key: 管理密钥
            file_data: 文件数据

        Returns:
            文件上传响应

        Raises:
            ValueError: 当Paste不存在或权限验证失败时
        """
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")

        if not PasteService._verify_admin_key(paste, admin_key):
            raise ValueError("管理密钥错误")

        # 生成文件ID
        import uuid

        file_id = str(uuid.uuid4())

        # 解码文件数据
        import base64

        try:
            file_bytes = base64.b64decode(file_data.encrypted_file)
        except Exception as e:
            raise ValueError(f"文件数据格式错误: {e}") from None

        # 保存文件到存储
        storage_path = PasteService._save_file_to_storage(paste_id, file_id, file_bytes)

        # 计算文件校验和
        checksum = hashlib.sha256(file_bytes).hexdigest()

        # 创建文件记录
        file_record = File(
            id=file_id,
            paste_id=paste_id,
            file_name_encrypted=file_data.encrypted_metadata.get("file_name", ""),
            mime_type=file_data.encrypted_metadata.get(
                "mime_type", "application/octet-stream"
            ),
            file_size=len(file_bytes),
            storage_path=storage_path,
            checksum=checksum,
        )

        db.add(file_record)

        # 如果是已发布状态，更新为编辑状态
        if str(paste.status) == "published":  # type: ignore
            paste.status = "edited"  # type: ignore
            paste.updated_at = datetime.utcnow()  # type: ignore

        db.commit()

        return FileUploadResponse(file_id=file_id)

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
        paste.published_at = datetime.utcnow()  # type: ignore
        paste.updated_at = datetime.utcnow()  # type: ignore

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
            paste_id=paste_id, admin_key=admin_key, encryption_key=encryption_key
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

        # 检查是否过期
        from datetime import datetime as dt_type

        paste_expire_at: dt_type = paste.expire_at  # type: ignore
        if paste_expire_at is not None and datetime.utcnow() > paste_expire_at:
            raise ValueError("Paste已过期")

        # 获取文件列表
        files = db.query(File).filter(File.paste_id == paste_id).all()
        file_infos = [
            FileInfo(
                id=str(f.id),  # type: ignore
                size=int(f.file_size),  # type: ignore
                encrypted_name=str(f.file_name_encrypted),  # type: ignore
                url=f"/api/pastes/{paste_id}/files/{f.id}",
            )
            for f in files
        ]

        return PasteResponse(
            title=str(paste.title) if paste.title else None,  # type: ignore
            type=str(paste.type) if paste.type else "txt",  # type: ignore
            status=str(paste.status),  # type: ignore
            files=file_infos,
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

        # 检查是否过期
        from datetime import datetime as dt_type

        paste_expire_at: dt_type = paste.expire_at  # type: ignore
        if paste_expire_at is not None and datetime.utcnow() > paste_expire_at:
            raise ValueError("Paste已过期")

        # 检查查看次数限制并增加计数
        paste_max_views = int(paste.max_views or -1)  # type: ignore
        paste_view_count = int(paste.view_count or 0)  # type: ignore
        if paste_max_views > 0 and paste_view_count >= paste_max_views:
            raise ValueError("Paste已达到最大查看次数")

        # 增加查看次数
        paste.view_count = paste_view_count + 1  # type: ignore
        db.commit()

        content_path = paste.content_path  # type: ignore
        if content_path is None or str(content_path).strip() == "":
            raise ValueError("Paste内容为空")

        # 读取内容
        encrypted_content = PasteService._read_content_from_file(str(content_path))

        response = PasteContentResponse(
            encrypted_content=encrypted_content, content=None
        )

        # 如果提供了解密密钥，尝试解密
        if encryption_key:
            try:
                key_bytes = urlsafe_str_to_key(encryption_key)
                content_bytes = str_to_bytes(encrypted_content)
                decrypted_bytes = decrypt_with_key(content_bytes, key_bytes)
                response.content = decrypted_bytes.decode()
            except Exception:
                # 解密失败，只返回加密内容
                print("解密失败，返回加密内容")
                pass

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

        paste.updated_at = datetime.utcnow()  # type: ignore
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
