from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import create_tables
from app.routers import rolls, defects, videos, websocket as ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FabricEye AI 验布系统后端 API",
    version="1.0.0",
    lifespan=lifespan
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(rolls.router, prefix=settings.API_V1_STR)
app.include_router(defects.router, prefix=settings.API_V1_STR)
app.include_router(videos.router, prefix=settings.API_V1_STR)
# WebSocket 路由已在 websocket.py 中定义
app.include_router(ws_router.router)

@app.get("/api/debug/config", tags=["Debug"])
async def get_debug_config():
    from app.core.config import settings
    return {
        "AI_PROVIDER": settings.AI_PROVIDER,
        "QWEN_API_KEY_SET": bool(settings.QWEN_API_KEY),
        "QWEN_API_KEY_PREFIX": settings.QWEN_API_KEY[:5] + "..." if settings.QWEN_API_KEY else None,
        "QWEN_FLASH_MODEL": settings.QWEN_FLASH_MODEL,
        "QWEN_API_BASE_URL": settings.QWEN_API_BASE_URL,
        "CAMERA_TYPE": settings.CAMERA_TYPE
    }

@app.get("/debug/engines", tags=["Debug"])
async def debug_engines():
    from app.routers.rolls import active_engines
    return {"active_engines_keys": list(active_engines.keys()), "active_engines": str(active_engines)}

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
