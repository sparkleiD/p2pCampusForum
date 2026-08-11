"""P2P 消息路由器 - 根据 msg_type 分发到不同处理器"""

from typing import Callable, Dict

class MessageRouter:
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register(self, msg_type: str, handler: Callable):
        """注册消息类型对应的处理函数"""
        self._handlers[msg_type] = handler

    def route(self, data: dict, sender_peer_id: str):
        """路由消息到对应处理器"""
        msg_type = data.get('msg_type')
        if not msg_type:
            print("[ROUTER] ⚠️ 收到无 msg_type 的消息，忽略")
            return
        handler = self._handlers.get(msg_type)
        if handler:
            try:
                handler(data, sender_peer_id)
            except Exception as e:
                print(f"[ROUTER] ❌ 处理消息 {msg_type} 时出错: {e}")
        else:
            print(f"[ROUTER] ℹ️ 未注册消息类型: {msg_type}")