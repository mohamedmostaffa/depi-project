"""
BrandMind — FastAPI Application Factory
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yaml
from dotenv import load_dotenv

load_dotenv()

from src.api.routes import _purge_expired_customer_ignored, router

logger = logging.getLogger(__name__)


async def _customer_ignore_retention_worker():
    while True:
        try:
            await asyncio.to_thread(_purge_expired_customer_ignored)
        except Exception:
            logger.exception("Could not purge expired customer-ignored conversations")
        await asyncio.sleep(5 * 60)


def create_app(config_path: str = "config/settings.yaml") -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app):
        task = asyncio.create_task(_customer_ignore_retention_worker())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(
        title="BrandMind API",
        description="Grounded AI Customer-Service & Sales System for RLVNT",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def prevent_private_api_caching(request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith(("/api/v1/customer", "/api/v1/conversations", "/api/v1/admin",
                            "/customer", "/conversations", "/admin")):
            response.headers["Cache-Control"] = "private, no-store"
        return response

    # CORS configuration
    configured = os.getenv("BRANDMIND_CORS_ORIGINS")
    if configured is not None:
        origins = [value.strip().rstrip("/") for value in configured.split(",") if value.strip()]
    elif os.getenv("ENVIRONMENT", "development").lower() == "production":
        origins = []
    else:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                origins = cfg.get("server", {}).get("cors_origins", ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"])
        except Exception:
            origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"]
    origins = [origin for origin in origins if origin != "*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )

    app.include_router(router, prefix="/api/v1")
    app.include_router(router)  # Also expose root /health, /orders, /products

    return app


app = create_app()
