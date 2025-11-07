"""
清理任务相关的Pydantic模型
"""


from pydantic import BaseModel, Field


class CleanupTaskEnum:
    """清理任务类型枚举"""

    EXPIRED_DRAFTS = "expired_drafts"
    EXPIRED_PASTES = "expired_pastes"
    EXPIRED_MEMBERS = "expired_members"


class CleanupRequest(BaseModel):
    """清理任务请求"""

    tasks: list[str] = Field(..., description="要执行的清理任务列表")


class CleanupTaskResult(BaseModel):
    """单个清理任务结果"""

    task_name: str = Field(..., description="任务名称")
    success: bool = Field(..., description="是否执行成功")
    deleted_count: int = Field(..., description="删除的记录数量")
    message: str = Field(..., description="执行结果消息")
    error: str | None = Field(default=None, description="错误信息（如果有）")


class CleanupResponse(BaseModel):
    """清理任务响应"""

    success: bool = Field(..., description="整体是否执行成功")
    total_deleted: int = Field(..., description="总删除记录数")
    task_results: list[CleanupTaskResult] = Field(..., description="各任务执行结果")
    message: str = Field(..., description="总体执行消息")


class InternalAuthRequest(BaseModel):
    """内部认证请求"""

    internal_token: str = Field(..., description="内部认证令牌")
