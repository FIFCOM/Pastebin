"""
Controllers层 - 路由控制器
"""

from .health_controller import router as health_router
from .user_controller import router as user_router

__all__ = ["user_router", "health_router"]
