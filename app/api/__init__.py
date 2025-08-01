from .bills import router as bills_router
from .representatives import router as representatives_router
from .admin import router as admin_router
from .widget import router as widget_router

__all__ = ["bills_router", "representatives_router", "admin_router", "widget_router"]
