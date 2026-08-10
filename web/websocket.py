# web/websocket.py
"""
WebSocket 实时推送模块.

当有新帖子或新评论审核通过时, 主动推送给所有在线客户端.
"""

import json
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """
    WebSocket 连接管理器.

    负责管理所有活跃连接, 并提供广播功能.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """接受新连接并加入管理列表"""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """从管理列表中移除断开连接的客户端"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """向所有活跃连接广播消息"""
        if not self.active_connections:
            return

        data = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                # 发送失败时, 标记为断开, 由 disconnect 处理
                pass


# 全局连接管理器实例
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端点.

    客户端连接后, 保持长连接以接收实时推送.
    """
    await manager.connect(websocket)
    try:
        # 保持连接活跃, 接收客户端消息（心跳或ping）
        while True:
            # 接收客户端消息（可用于心跳检测）
            data = await websocket.receive_text()
            # 如果收到 ping, 回复 pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket 异常: {e}")
        manager.disconnect(websocket)


# ============ 对外广播函数 ============

async def broadcast_new_post(post_data: dict):
    """
    广播新帖子上线.

    Args:
        post_data: 帖子数据字典, 包含 post_id, content, nickname, final_verdict 等
    """
    await manager.broadcast({
        "type": "new_post",
        "data": post_data
    })


async def broadcast_new_comment(comment_data: dict):
    """
    广播新评论上线.

    Args:
        comment_data: 评论数据字典, 包含 comment_id, post_id, content, nickname, final_verdict 等
    """
    await manager.broadcast({
        "type": "new_comment",
        "data": comment_data
    })