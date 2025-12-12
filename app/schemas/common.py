"""
通用Pydantic模型
"""

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """通用消息响应"""

    message: str
    detail: str | None = None


class ErrorResponse(BaseModel):
    """错误响应"""

    error: str
    detail: str | None = None
    code: str | None = None


class PaginationParams(BaseModel):
    """分页参数"""

    page: int = 1
    size: int = 10


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str
    version: str
    timestamp: str
