"""
Controllers层 - 路由控制器
"""

from .admin_controller import router as admin_router
from .api_key_controller import router as api_key_router
from .cleanup_controller import router as cleanup_router
from .collab_room_controller import router as collab_room_router
from .config_controller import router as config_router
from .docs_controller import router as docs_router
from .health_controller import router as health_router
from .install_controller import router as install_router
from .paste_controller import router as paste_router
from .user_controller import router as user_router
from .user_favorite_controller import router as user_favorite_router
from .user_history_controller import router as user_history_router

__all__ = [
    "user_router",
    "admin_router",
    "health_router",
    "api_key_router",
    "paste_router",
    "user_favorite_router",
    "user_history_router",
    "collab_room_router",
    "cleanup_router",
    "config_router",
    "docs_router",
    "install_router",
]
