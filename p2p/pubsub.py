"""
PubSub 发布订阅模块.
"""

import json
import base64
from typing import Callable, Optional
from libp2p.pubsub.gossipsub import GossipSub
from libp2p.pubsub.pubsub import Pubsub
from .router import MessageRouter
from .protocol import MsgType
from config import PUBSUB_TOPIC


class PubSubManager:
    """
    PubSub 管理器.

    使用 GossipSub 协议，需要传入 degree/degree_low/degree_high 参数.
    """

    def __init__(self, host, topic: str = None):
        self.host = host
        self.topic = topic or PUBSUB_TOPIC
        self._pubsub: Optional[GossipSub] = None

    def setup(self):
        """初始化 PubSub（Host 需已启动）"""
        # 修正：用列表包装 host
        gossipsub = GossipSub(
            protocols=[],
            degree=3,
            degree_low=2,
            degree_high=6
        )
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
        subscription = await self._pubsub.subscribe(self.topic)
        # 从 receive_channel 中迭代消息
        async for msg in subscription.receive_channel:

            try:
                raw = msg.data.decode("utf-8")
                data = json.loads(raw)
                # 确保 data 是字典
                if not isinstance(data, dict):
                    print(f"[PUBSUB] ⚠️ 收到非字典消息，忽略: {raw[:100]}")
                    continue
            except Exception as e:
                print(f"[PUBSUB] ⚠️ 解析消息失败: {e}, 原始数据前50字符: {msg.data[:50]}")
                continue

            data = json.loads(msg.data.decode("utf-8"))
            # 安全提取 sender_peer_id
            if hasattr(msg.from_id, 'pretty'):
                sender_peer_id = msg.from_id.pretty()
            else:
                # 使用 base64 编码避免解码错误
                sender_peer_id = base64.b64encode(msg.from_id).decode('ascii')
            callback(data, sender_peer_id)

    def setup_router(self) -> Callable:
        router = MessageRouter()

        def handle_audit_request(data: dict, sender: str):
            print(f"[PUBSUB] 📩 审核请求来自 {sender}: {data.get('payload', {}).get('content', '')[:50]}...")
            # TODO: 调用本地 AI 审核，发送 audit_response

        def handle_audit_response(data: dict, sender: str):
            print(f"[PUBSUB] 📩 审核回复来自 {sender}: {data.get('payload', {}).get('verdict')}")
            # TODO: 收集投票，触发共识

        def handle_post_publish(data: dict, sender: str):
            print(f"[PUBSUB] 📩 新帖子来自 {sender}: {data.get('payload', {}).get('post_id')}")
            # TODO: 保存到本地数据库，触发 WebSocket 推送

        def handle_comment_publish(data: dict, sender: str):
            print(f"[PUBSUB] 📩 新评论来自 {sender}: {data.get('payload', {}).get('comment_id')}")
            # TODO: 保存到本地数据库

        def handle_sync_request(data: dict, sender: str):
            print(f"[PUBSUB] 📩 同步请求来自 {sender}")
            # TODO: 响应全量数据

        def handle_sync_response(data: dict, sender: str):
            print(f"[PUBSUB] 📩 同步响应来自 {sender}")
            # TODO: 将接收到的数据保存到本地数据库

        def handle_consensus_request(data: dict, sender: str):
            print(f"[PUBSUB] 📩 共识请求来自 {sender}: {data.get('payload', {}).get('content_id')}")
            # TODO: 参与共识投票

        def handle_consensus_vote(data: dict, sender: str):
            print(f"[PUBSUB] 📩 共识投票来自 {sender}: {data.get('payload', {}).get('verdict')}")
            # TODO: 收集投票

        router.register(MsgType.AUDIT_REQUEST, handle_audit_request)
        router.register(MsgType.AUDIT_RESPONSE, handle_audit_response)
        router.register(MsgType.POST_PUBLISH, handle_post_publish)
        router.register(MsgType.COMMENT_PUBLISH, handle_comment_publish)
        router.register(MsgType.SYNC_REQUEST, handle_sync_request)
        router.register(MsgType.SYNC_RESPONSE, handle_sync_response)
        router.register(MsgType.CONSENSUS_REQUEST, handle_consensus_request)
        router.register(MsgType.CONSENSUS_VOTE, handle_consensus_vote)

        print("[PUBSUB] ✅ P2P 消息路由器已初始化，所有处理器已注册")
        return router.route