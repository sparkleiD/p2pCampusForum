"""
libp2p Host 管理模块.
"""

from libp2p import new_host
from libp2p.crypto.ed25519 import create_new_key_pair
from libp2p.security.noise.transport import PROTOCOL_ID as NOISE_PROTOCOL_ID, Transport as NoiseTransport

# 导入 Yamux 组件
from libp2p.stream_muxer.yamux.yamux import Yamux
from libp2p.custom_types import TProtocol

async def create_host(port: int = None):
    """
    创建 libp2p Host（不启动监听）。

    Args:
        port: P2P 监听端口（仅用于日志，实际监听由 host.run() 控制）

    Returns:
        未启动的 Host 实例
    """
    key_pair = create_new_key_pair()
    host = new_host(key_pair=key_pair)
    return host


def get_peer_id(host) -> str:
    """获取节点的 PeerID"""
    return host.get_id().pretty()


def get_listen_addrs(host) -> list:
    """获取节点的所有监听地址"""
    return [str(addr) for addr in host.get_addrs()]


async def stop_host(host):
    """停止 Host 并释放资源"""
    if host:
        await host.close()