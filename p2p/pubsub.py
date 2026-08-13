"""
PubSub 发布订阅模块.
"""

import json
from typing import Callable, Optional
from libp2p.pubsub.gossipsub import GossipSub
from libp2p.pubsub.pubsub import Pubsub
from libp2p.custom_types import TProtocol
from .router import MessageRouter
from .protocol import MsgType
from config import PUBSUB_TOPIC
from . import handler

GOSSIPSUB_PROTOCOL_ID = TProtocol("/meshsub/1.0.0")

class PubSubManager:
    """
    PubSub 管理器.

    使用 GossipSub 协议，需要传入 degree/degree_low/degree_high 参数.
    """

    def __init__(self, host, topic: str = None):
        self.host = host
        self.topic = topic or PUBSUB_TOPIC
        self._pubsub: Optional[Pubsub] = None
        self._gossipsub: Optional[GossipSub] = None   # 新增，用于启动服务

    def setup(self):
        """初始化 PubSub（Host 需已启动）"""
        gossipsub = GossipSub(
            protocols=[GOSSIPSUB_PROTOCOL_ID],   # 必须指定协议 ID
            degree=3,
            degree_low=2,
            degree_high=6,
            heartbeat_interval=2
        )
        self._gossipsub = gossipsub
        self._pubsub = Pubsub(self.host, gossipsub)
        print(f"[PUBSUB] ✅ PubSub 已初始化 (GossipSub)，话题: {self.topic}")

    async def publish(self, data: dict):
        """向话题发布消息"""
        if not self._pubsub:
            raise RuntimeError("PubSub 未初始化，请先调用 setup()")
        message = json.dumps(data).encode("utf-8")
        await self._pubsub.publish(self.topic, message)

    async def run_receiver(self, callback: Callable):
        """
        持续从 PubSub 接收消息并调用回调。
        此方法应作为后台任务在 Trio Nursery 中启动。
        """
        if not self._pubsub:
            raise RuntimeError("PubSub 未初始化，请先调用 setup()")
        
        # 获取本节点 PeerID 的两种形式：可读字符串用于日志，原始字节用于比较
        my_peer_id_pretty = self.host.get_id().pretty()

        subscription = await self._pubsub.subscribe(self.topic)
        # 从 receive_channel 中迭代消息
        async for msg in subscription.receive_channel:
            try:
                raw = msg.data.decode("utf-8")
                data = json.loads(raw)
                if not isinstance(data, dict):
                    print(f"[PUBSUB] ⚠️ 收到非字典消息，忽略: {raw[:100]}")
                    continue
            except Exception as e:
                print(f"[PUBSUB] ⚠️ 解析消息失败: {e}, 原始数据前50字符: {msg.data[:50]}")
                continue

            sender_peer_id = data.get("sender")

            # 切换下面两行代码启用|关闭本地回环测试
            if False:
            # if sender_peer_id == my_peer_id_pretty:
                print(f"[PUBSUB] ⚠️ 收到自己发送的消息，忽略: {data.get('msg_type')}")
                continue

            await callback(data, sender_peer_id, self) #此处 callback 是 router.route

    def setup_router(self) -> Callable:
        """注册所有消息处理器，返回路由函数"""
        router = MessageRouter()

        router.register(MsgType.AUDIT_REQUEST, handler.handle_audit_request)
        router.register(MsgType.AUDIT_RESPONSE, handler.handle_audit_response)
        router.register(MsgType.POST_PUBLISH, handler.handle_post_publish)
        router.register(MsgType.COMMENT_PUBLISH, handler.handle_comment_publish)
        router.register(MsgType.SYNC_REQUEST, handler.handle_sync_request)
        router.register(MsgType.SYNC_RESPONSE, handler.handle_sync_response)
        router.register(MsgType.CONSENSUS_REQUEST, handler.handle_consensus_request)
        router.register(MsgType.CONSENSUS_VOTE, handler.handle_consensus_vote)

        print("[PUBSUB] ✅ P2P 消息路由器已初始化，所有处理器已注册")
        return router.route