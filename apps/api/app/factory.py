from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api import health
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.request_context import REQUEST_ID_HEADER, RequestContextMiddleware
from app.core.sentry import configure_sentry
from app.services.ai.base import LLMProvider
from app.services.ai.factory import build_llm_provider
from app.services.auth.base import AuthProvider
from app.services.auth.supabase import SupabaseAuthProvider

logger = structlog.get_logger(__name__)


def create_app(
    settings: Settings | None = None,
    auth_provider: AuthProvider | None = None,
    llm_provider: LLMProvider | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    configure_sentry(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        app.state.database = Database(settings)
        app.state.redis = (
            Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
            if settings.redis_url
            else None
        )
        app.state.auth_provider = auth_provider or SupabaseAuthProvider(settings)
        app.state.llm = llm_provider or build_llm_provider(settings)
        logger.info(
            "api_started",
            environment=settings.environment,
            ai_provider=app.state.llm.name if app.state.llm else "disabled",
            redis_configured=app.state.redis is not None,
        )
        try:
            yield
        finally:
            if app.state.llm is not None:
                await app.state.llm.aclose()
            await app.state.auth_provider.aclose()
            if app.state.redis is not None:
                await app.state.redis.aclose()
            await app.state.database.dispose()
            logger.info("api_stopped")

    app = FastAPI(
        title="Workaholic API",
        version="0.1.0",
        lifespan=lifespan,
        # Interactive docs are a development aid, not a public surface.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    register_error_handlers(app)

    # Added first = innermost. CORS stays outermost so even error responses carry CORS headers.
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
        max_age=600,
    )

    app.include_router(health.router)
    app.include_router(api_router)
    return app
