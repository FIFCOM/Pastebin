"""
Paste控制器 - REST API路由
"""

import base64
import io

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi import (
    File as FastAPIFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import MessageResponse
from app.schemas.paste import (
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
)
from app.services.paste_service import PasteService

# 创建路由器
router = APIRouter(prefix="/api/pastes", tags=["Paste"])


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
        PasteService.update_paste_content(db, paste_id, admin_key, content_data)
        return MessageResponse(message="内容更新成功")
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


@router.post("/{paste_id}/files", response_model=FileUploadResponse)
async def upload_file_json(
    paste_id: str,
    file_data: FileUploadRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    上传文件（JSON格式，用于客户端加密）

    需要在Authorization头中提供admin_key: Bearer {admin_key}

    - **encrypted_file**: Base64编码的加密文件数据
    - **encrypted_metadata**: 加密的文件元数据
    """
    admin_key = _get_admin_key_from_header(authorization)

    try:
        return PasteService.upload_file(db, paste_id, admin_key, file_data)
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


@router.post("/{paste_id}/files/upload", response_model=FileUploadResponse)
async def upload_file_multipart(
    paste_id: str,
    file: UploadFile = FastAPIFile(...),
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    上传文件（multipart/form-data格式，用于服务端加密）

    需要在Authorization头中提供admin_key: Bearer {admin_key}
    """
    admin_key = _get_admin_key_from_header(authorization)

    try:
        # 读取文件内容
        file_content = await file.read()

        # 构造文件数据
        file_data = FileUploadRequest(
            encrypted_file=base64.b64encode(file_content).decode(),
            encrypted_metadata={
                "file_name": file.filename or "unknown",
                "mime_type": file.content_type or "application/octet-stream",
            },
        )

        return PasteService.upload_file(db, paste_id, admin_key, file_data)
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


@router.get("/{paste_id}/content", response_model=PasteContentResponse)
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
    encryption_key: str | None = Query(None, description="解密密钥（可选）"),
    db: Session = Depends(get_db),
):
    """
    获取文件

    - **encryption_key**: 解密密钥（可选，如果提供且正确则解密文件名和内容）

    返回文件流，Content-Disposition: attachment; filename="filename"
    """
    try:
        from pathlib import Path

        from app.models.paste import File, Paste
        from config.config import settings

        # 获取文件记录
        file_record = (
            db.query(File)
            .join(Paste)
            .filter(File.id == file_id, File.paste_id == paste_id)
            .first()
        )

        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在"
            )

        # 检查Paste状态
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if not paste or str(paste.status) == "draft":  # type: ignore
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Paste不存在或不可访问"
            )

        # 读取文件
        file_path = Path(settings.data_dir) / str(file_record.storage_path)  # type: ignore
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在"
            )

        with open(file_path, "rb") as f:
            file_content = f.read()

        # 获取文件名
        encrypted_filename = str(file_record.file_name_encrypted)  # type: ignore
        filename = "encrypted_file"

        # 如果提供了解密密钥，尝试解密文件名和内容
        if encryption_key:
            try:
                from app.core.security import (
                    decrypt_with_key,
                    str_to_bytes,
                    urlsafe_str_to_key,
                )

                # 解密文件名
                key_bytes = urlsafe_str_to_key(encryption_key)
                encrypted_name_bytes = str_to_bytes(encrypted_filename)
                decrypted_name_bytes = decrypt_with_key(encrypted_name_bytes, key_bytes)
                filename = decrypted_name_bytes.decode()

                # 解密文件内容
                decrypted_content = decrypt_with_key(file_content, key_bytes)
                file_content = decrypted_content

            except Exception:
                # 解密失败，使用原始数据
                pass

        # 返回文件流
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=str(file_record.mime_type) or "application/octet-stream",  # type: ignore
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(file_content)),
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
        return MessageResponse(message="Paste删除成功")
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
