import asyncio
import contextlib
import warnings
from contextlib import asynccontextmanager
from urllib.parse import urlparse, urlunparse

warnings.filterwarnings("ignore", message="Deserializing unregistered type")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from starlette.requests import Request

from app.config import get_settings
from app.db import init_db
from app.graph.content_pipeline import compile_content_graph
from app.graph.pipeline import compile_graph
from app.routes import (
    assessment,
    auth,
    gap_analysis,
    health,
    learning_plan,
    materials,
    roles,
    skills,
    user,
)
from app.services.session_cleanup import cleanup_stale_sessions

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    parsed_db_url = urlparse(settings.database_url)
    if parsed_db_url.scheme not in ("postgresql+asyncpg",):
        raise RuntimeError(
            f"DATABASE_URL must use the 'postgresql+asyncpg' scheme, got '{parsed_db_url.scheme}'"
        )
    checkpoint_url = urlunparse(parsed_db_url._replace(scheme="postgresql"))
    cleanup_task = asyncio.create_task(cleanup_stale_sessions())
    async with AsyncPostgresSaver.from_conn_string(checkpoint_url) as checkpointer:
        await checkpointer.setup()
        app.state.graph = compile_graph(checkpointer)
        app.state.content_graph = compile_content_graph(checkpointer)
        yield
    cleanup_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await cleanup_task


app = FastAPI(
    title="OpenLearning API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(assessment.router, prefix="/api")
app.include_router(roles.router, prefix="/api")
app.include_router(gap_analysis.router, prefix="/api")
app.include_router(learning_plan.router, prefix="/api")
app.include_router(materials.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth")
app.include_router(user.router, prefix="/api/user")


def register_anthropic_error_handlers(application: FastAPI) -> None:
    """Register global exception handlers for Anthropic SDK errors."""
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        AuthenticationError,
        InternalServerError,
        RateLimitError,
    )

    from app.services.ai import classify_anthropic_error

    async def _handler(_request: Request, exc: Exception) -> JSONResponse:
        result = classify_anthropic_error(exc)
        if not result:
            return JSONResponse(
                status_code=500, content={"detail": "An unexpected error occurred."}
            )
        status, detail, headers = result
        return JSONResponse(status_code=status, content={"detail": detail}, headers=headers)

    for exc_type in (
        AuthenticationError,
        RateLimitError,
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
    ):
        application.add_exception_handler(exc_type, _handler)


register_anthropic_error_handlers(app)
