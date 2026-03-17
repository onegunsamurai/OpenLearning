import asyncio
import contextlib
import os
import warnings
from contextlib import asynccontextmanager

warnings.filterwarnings("ignore", message="Deserializing unregistered type")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import get_settings
from app.db import init_db
from app.graph.pipeline import compile_graph
from app.routes import assessment, gap_analysis, health, learning_plan, roles, skills
from app.services.session_cleanup import cleanup_stale_sessions

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    os.makedirs("data", exist_ok=True)
    cleanup_task = asyncio.create_task(cleanup_stale_sessions())
    async with AsyncSqliteSaver.from_conn_string("./data/checkpoints.db") as checkpointer:
        app.state.graph = compile_graph(checkpointer)
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
