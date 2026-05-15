from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import categories, contacts, frontend, health, users, wishlists
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.pool import close_db_pool, init_db_pool, init_schema
from app.middleware.request_logging import log_requests


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} in {settings.app_env} environment")
    await init_db_pool()
    if settings.db_apply_schema_on_startup:
        logger.info("Applying database schema on startup")
        await init_schema()
        logger.info("Database schema applied")

    yield

    logger.info("Shutting down application")
    await close_db_pool()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    swagger_ui_parameters={
        "supportedSubmitMethods": [],
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(log_requests)

app.include_router(health.router)
app.include_router(frontend.router)
app.include_router(users.router)
app.include_router(contacts.router)
app.include_router(categories.router)
app.include_router(wishlists.router)
