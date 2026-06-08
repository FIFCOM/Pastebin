"""
运行配置相关的 Pydantic 模型
"""

from typing import Literal

from pydantic import BaseModel, Field

RuntimeSettingKey = Literal[
    "MAX_UPLOAD_FILE_SIZE",
    "MAX_PASTE_TOTAL_UPLOAD_SIZE",
    "MAX_CHUNK_SIZE",
    "UPLOAD_EXPIRE_SECONDS",
    "MAX_CONCURRENT_UPLOADS",
    "COLLAB_ROOM_MAX_MEMBERS",
]


class RuntimeSettingItem(BaseModel):
    """运行配置响应项"""

    key: RuntimeSettingKey
    value: int
    default_value: int
    label: str
    group: str
    unit: str
    description: str
    allow_zero: bool
    min_value: int
    max_value: int | None = None


class RuntimeSettingsResponse(BaseModel):
    """运行配置列表响应"""

    settings: list[RuntimeSettingItem]


class RuntimeSettingUpdate(BaseModel):
    """运行配置更新项"""

    key: RuntimeSettingKey
    value: int = Field(..., description="配置值")


class RuntimeSettingsUpdateRequest(BaseModel):
    """运行配置批量更新请求"""

    settings: list[RuntimeSettingUpdate] = Field(..., min_length=1)
