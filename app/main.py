from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import categories, contacts, frontend, health, users, wishlists
from app.core.config import settings
from app.db.pool import close_db_pool, init_db_pool, init_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_pool()
    if settings.db_apply_schema_on_startup:
        await init_schema()

    yield

    await close_db_pool()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(frontend.router)
app.include_router(users.router)
app.include_router(contacts.router)
app.include_router(categories.router)
app.include_router(wishlists.router)
