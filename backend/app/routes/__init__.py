"""
API routes package for EmailGuardian.
"""

from app.routes.auth import router as auth_router
from app.routes.emails import router as emails_router
from app.routes.analytics import router as analytics_router

__all__ = ["auth_router", "emails_router", "analytics_router"]
