"""
FastAPI 主应用.

挂载所有路由、WebSocket 和静态文件.
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from web.routes import posts, comments, sync
from web.websocket import router as websocket_router

# 创建 FastAPI 应用
app = FastAPI(
    title="去中心化校园论坛",
    description="基于 P2P 和 AI 审核的去中心化校园论坛",
    version="1.0.0"
)

# 挂载路由
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(sync.router)
app.include_router(websocket_router)

# 静态文件目录
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# 挂载静态文件
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/")
async def root():
    """根路径返回前端页面"""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "去中心化校园论坛 API 运行中"}


@app.get("/health")
async def health():
    """健康检查接口"""
    return {"status": "ok"}