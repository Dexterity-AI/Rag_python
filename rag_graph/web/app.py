from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
import os
import sys

from cli import GraphRAGApp
from .routers import system, chat, collect, cache, data

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize GraphRAGApp in background to avoid blocking
    app.state.rag_app = GraphRAGApp()
    app.state.system_ready = False
    app.state.init_progress = "未开始"
    
    def init_rag():
        try:
            app.state.init_progress = "正在初始化系统模块..."
            if not app.state.rag_app.initialize():
                app.state.init_progress = "初始化系统模块失败"
                return
            
            app.state.init_progress = "正在加载知识库..."
            if not app.state.rag_app.build_knowledge_base():
                app.state.init_progress = "加载知识库失败"
                return
            
            app.state.system_ready = True
            app.state.init_progress = "初始化完成"
        except Exception as e:
            app.state.init_progress = f"初始化发生异常: {str(e)}"
            print(f"后台初始化异常: {e}")

    # Start the initialization in a thread
    loop = asyncio.get_event_loop()
    app.state.init_task = loop.run_in_executor(None, init_rag)
    
    yield
    
    # Shutdown: cleanup
    if hasattr(app.state, "rag_app") and app.state.rag_app:
        app.state.rag_app.cleanup()

def create_app() -> FastAPI:
    app = FastAPI(
        title="GraphRAG Web UI",
        description="智能图RAG旅游助手 Web API",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(system.router, prefix="/api/system", tags=["System"])
    app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
    app.include_router(collect.router, prefix="/api/collect", tags=["Collect"])
    app.include_router(cache.router, prefix="/api/cache", tags=["Cache"])
    app.include_router(data.router, prefix="/api/data", tags=["Data"])

    # Mount static files
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # SPA Fallback
    @app.get("/")
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        # Prevent API routes from hitting SPA fallback
        if path.startswith("api/"):
            return {"detail": "API route not found"}
        
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"detail": "Web UI not built"}

    return app
