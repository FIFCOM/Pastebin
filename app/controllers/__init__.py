"""
Controllers层 - 路由控制器
"""

from .api_key_controller import router as api_key_router
from .health_controller import router as health_router
from .paste_controller import router as paste_router
from .user_controller import router as user_router
from .user_paste_controller import router as user_paste_router

__all__ = ["user_router", "health_router", "api_key_router", "paste_router", "user_paste_router"]
