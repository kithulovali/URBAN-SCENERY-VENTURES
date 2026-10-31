import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure application logging once, before importing routers and services.
# Uvicorn may configure its own access logger independently.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

from core.config import settings
from core.database import init_db
from routers import (
    auth_router, users_router, products_router, orders_router,
    payments_router, ai_router, agents_router, platforms_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger(__name__)
    logger.info("Application startup: initializing database")
    try:
        init_db()
    except Exception:
        logger.exception("Application startup failed during database initialization")
        raise
    logger.info("Application startup: database initialization complete")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="FastAPI backend for Urban Scenery Ventures with database-grounded AI agents.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
for router in (auth_router, users_router, products_router, orders_router, payments_router, ai_router, agents_router, platforms_router):
    app.include_router(router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health & Info"])
def root():
    return {
        "project": settings.PROJECT_NAME, "version": settings.VERSION, "status": "online",
        "documentation": "/docs", "redoc": "/redoc",
        "endpoints": {
            "auth": f"{settings.API_V1_STR}/auth", "users": f"{settings.API_V1_STR}/users",
            "products": f"{settings.API_V1_STR}/products", "orders": f"{settings.API_V1_STR}/orders",
            "payments": f"{settings.API_V1_STR}/payments", "ai": f"{settings.API_V1_STR}/ai",
            "ai_agents": f"{settings.API_V1_STR}/ai/agents",
            "platforms": f"{settings.API_V1_STR}/platforms",
        },
    }


@app.get("/health", tags=["Health & Info"])
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
