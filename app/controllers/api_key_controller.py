"""
API Key控制器 - REST API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.api_key import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse
from app.services.api_key_service import ApiKeyService

# 创建路由器
router = APIRouter(prefix="/api/user/apikeys", tags=["API密钥管理"])


@router.get("", response_model=ApiKeyListResponse)
async def get_api_keys(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    获取API密钥列表

    返回当前用户的所有API密钥（不包含密钥本身）
    """
    return ApiKeyService.get_user_api_keys(db, current_user.id)


@router.post(
    "", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    api_key_data: ApiKeyCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    创建API密钥

    - **name**: API密钥名称

    返回创建的API密钥信息，包含密钥明文（仅此一次返回）
    """
    try:
        api_key = ApiKeyService.create_api_key(db, current_user.id, api_key_data)
        return api_key
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.delete("/{key_id}", response_model=MessageResponse)
async def delete_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    删除API密钥

    用户只能删除自己的API密钥
    """
    success = ApiKeyService.delete_api_key(db, current_user.id, key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API密钥不存在或无权限删除"
        )

    return MessageResponse(message="API密钥已删除")


@router.post("/cleanup-expired", response_model=MessageResponse)
async def cleanup_expired_api_keys(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    count = ApiKeyService.cleanup_expired_api_keys(db, current_user.id)
    return MessageResponse(message=f"已清理 {count} 个过期 API Key")
