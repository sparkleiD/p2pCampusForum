"""
libp2p Host 管理模块.
"""

from libp2p import new_host
from multiaddr import Multiaddr
from config import P2P_PORT


async def create_host(port: int = None):
    """
    创建并启动 libp2p Host.

    Args:
        port: P2P 监听端口，默认使用 config.P2P_PORT

    Returns:
        已启动的 Host 实例
    """
    if port is None:
        port = P2P_PORT

    # 构造监听地址
    listen_addr = Multiaddr(f"/ip4/0.0.0.0/tcp/{port}")

    # new_host 返回的 Host 已经自动启动，不需要再调用 start()
    host = new_host(listen_addrs=[listen_addr])

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