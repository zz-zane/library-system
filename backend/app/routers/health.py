from fastapi import APIRouter

from backend.app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "service": "library-system",
        "environment": settings.environment,
    }
