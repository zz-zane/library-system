from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_settings
from backend.app.routers.auth import router as auth_router
from backend.app.routers.books import router as books_router
from backend.app.routers.borrows import router as borrows_router
from backend.app.routers.health import router as health_router
from backend.app.routers.readers import router as readers_router
from backend.app.routers.users import router as users_router


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(books_router)
    application.include_router(readers_router)
    application.include_router(borrows_router)

    return application


app = create_app()
