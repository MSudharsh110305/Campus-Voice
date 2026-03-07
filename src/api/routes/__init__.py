"""
API routes package initialization.

Register all route modules.

✅ FIXED: Proper router return from create_api_router
✅ FIXED: Health router at root level (no /api prefix)
"""

from fastapi import APIRouter

from .students import router as students_router
from .complaints import router as complaints_router
from .authorities import router as authorities_router
from .admin import router as admin_router
from .health import router as health_router
from .petitions import router as petitions_router
from .auth import router as auth_router


def create_api_router() -> tuple[APIRouter, APIRouter]:
    """
    Create main API router with all sub-routers.

    Returns:
        Tuple of (api_router, root_router):
        - api_router: Routes under /api prefix
        - root_router: Routes at root level (health checks)
    """
    # API routes (with /api prefix)
    api_router = APIRouter(prefix="/api")

    # Register all API routers
    api_router.include_router(auth_router)       # POST /api/auth/refresh (public)
    api_router.include_router(students_router)
    api_router.include_router(complaints_router)
    api_router.include_router(authorities_router)
    api_router.include_router(admin_router)
    api_router.include_router(petitions_router)
    
    # Health checks at root level (no /api prefix)
    # This allows /health instead of /api/health
    root_router = APIRouter()
    root_router.include_router(health_router)
    
    return api_router, root_router


__all__ = [
    "create_api_router",
    "auth_router",
    "students_router",
    "complaints_router",
    "authorities_router",
    "admin_router",
    "health_router",
    "petitions_router",
]
