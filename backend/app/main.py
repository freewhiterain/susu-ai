from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.database import create_db_and_tables
from app.api.documents import router as docs_router
from app.api.chat import router as chat_router
from app.api.logs import router as logs_router
from app.api.webhooks import router as webhook_router
from app.api.settings import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    create_db_and_tables()
    from loguru import logger
    logger.info("小苏 AI 助手启动完毕")
    yield
    logger.info("小苏 AI 助手已关闭")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="小苏 AI 助手",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(docs_router)
    app.include_router(chat_router)
    app.include_router(logs_router)
    app.include_router(webhook_router)
    app.include_router(settings_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
