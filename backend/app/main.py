"""
FastAPI main application — entry point for the RAQ Chatbot backend.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────
    print("🚀 RAQ Chatbot Backend starting...")
    print(f"   Mock LLM mode: {settings.USE_MOCK_LLM}")

    # Initialize LangGraph checkpointer
    checkpointer = None
    try:
        from app.core.db import get_checkpointer
        checkpointer = await get_checkpointer()
        print("   ✅ LangGraph Checkpointer initialized")
    except Exception as e:
        print(f"   ⚠️ Checkpointer init failed (non-critical): {e}")

    # We no longer register CopilotKit here due to 404 routing bugs with ASGI.
    # It is registered synchronously at the module level.

    yield

    # ── Shutdown ─────────────────────────────────────────
    print("👋 RAQ Chatbot Backend shutting down...")


# ── Create FastAPI App ───────────────────────────────────────
app = FastAPI(
    title="RAQ Chatbot API",
    description="Multi-Tenant Agentic RAG & Multi-Agent Quiz Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Đăng ký CopilotKit ở ngay ngoài luồng chính (không để trong lifespan)
# để đảm bảo FastAPI nhận diện được route ngay từ đầu, tránh lỗi 404.
from app.api.routes.copilotkit import register_copilotkit
print("Registering_agent_RAQ")
register_copilotkit(app, checkpointer=None)
print("Complete register!")

# ── CORS Middleware ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Include API Routers ─────────────────────────────────────
from app.api.routes.auth import router as auth_router
from app.api.routes.libraries import router as libraries_router
from app.api.routes.documents import router as documents_router
from app.api.routes.quizzes import router as quizzes_router

app.include_router(auth_router)
app.include_router(libraries_router)
app.include_router(documents_router)
app.include_router(quizzes_router)


# ── Health Check ─────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
async def health_check():
    return {
        "status": "ok",
        "mock_mode": settings.USE_MOCK_LLM,
    }
