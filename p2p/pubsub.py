"""
PubSub 发布订阅模块.
"""

import json
from typing import Callable, Optional
from libp2p.pubsub.gossipsub import GossipSub
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
        self._pubsub = GossipSub(
            [self.host],   # ← 这里用列表包装
            degree=6,
            degree_low=4,
            degree_high=12
        )
        print(f"✅ PubSub 已初始化 (GossipSub)，话题: {self.topic}")

    def publish(self, data: dict):
        """向话题发布消息"""
        if not self._pubsub:
            raise RuntimeError("PubSub 未初始化，请先调用 setup()")
        message = json.dumps(data).encode("utf-8")
        self._pubsub.publish(self.topic, message)

    def subscribe(self, callback: Callable):
        """
        订阅话题.

        Args:
            callback: 接收参数 (msg_data, sender_peer_id) 的函数
        """
        if not self._pubsub:
            raise RuntimeError("PubSub 未初始化，请先调用 setup()")

        def handler(msg):
            data = json.loads(msg.data.decode("utf-8"))
            # 注意：msg.from_id 可能是 PeerID 对象，需要调用 .pretty()
            callback(data, msg.from_id.pretty())

        self._pubsub.subscribe(self.topic, handler)