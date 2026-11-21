"""
BrandMind — FastAPI Application Factory
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yaml

from src.api.routes import router


def create_app(config_path: str = "config/settings.yaml") -> FastAPI:
    app = FastAPI(
        title="BrandMind API",
        description="Grounded AI Customer-Service & Sales System for RLVNT",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration
    origins = ["*"]
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            origins = cfg.get("server", {}).get("cors_origins", ["*"])
    except Exception:
        pass

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")
    app.include_router(router)  # Also expose root /health, /orders, /products

    return app


app = create_app()
