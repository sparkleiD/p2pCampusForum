import socket
import uuid
import trio
from zeroconf import ServiceInfo, ServiceListener, Zeroconf

from config import MDNS_SERVICE_NAME, MDNS_SERVICE_TYPE, WEB_PORT ,P2P_SERVICE_TYPE


# ---------- 工具函数 ----------
def _get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"[DISCOVERY] 🐞 _get_local_ip() 返回: {ip}")
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


# ---------- 同步注册函数 ----------
def _register_service_sync(info: ServiceInfo) -> Zeroconf:
    zc = Zeroconf()
    zc.register_service(info)
    return zc


# ---------- 异步包装（在线程中运行） ----------
async def async_register_mdns_service(
    port: int = None,
    service_name: str = None,
    peer_id: str = None
):
    if port is None:
        port = WEB_PORT

    if service_name is None:
        if peer_id:
            suffix = peer_id[-6:] if len(peer_id) >= 6 else peer_id
            service_name = f"{MDNS_SERVICE_NAME}-{suffix}"
        else:
            service_name = f"{MDNS_SERVICE_NAME}-{uuid.uuid4().hex[:6]}"

    ip = _get_local_ip()
    info = ServiceInfo(
        MDNS_SERVICE_TYPE,
        f"{service_name}.{MDNS_SERVICE_TYPE}",
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={"path": "/", "peer_id": peer_id or ""},
        server=f"{service_name}.local."
    )

    zc = await trio.to_thread.run_sync(_register_service_sync, info)
    print(f"[DISCOVERY] ✅ 唯一服务已注册: http://{service_name}.local:{port}")
    print(f"[DISCOVERY]    本机 IP: {ip}")
    return zc, service_name


# ---------- 固定别名注册 ----------
async def async_register_alias_service(port: int = None):
    if port is None:
        port = WEB_PORT

    ip = _get_local_ip()
    info = ServiceInfo(
        MDNS_SERVICE_TYPE,
        f"campusforum.{MDNS_SERVICE_TYPE}",
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={"path": "/", "is_leader": "true"},
        server="campusforum.local."
    )

    try:
        zc = await trio.to_thread.run_sync(_register_service_sync, info)
        print(f"[DISCOVERY] 👑 成功抢占固定域名: http://campusforum.local:{port} (当前为主节点)")
        return zc, True
    except Exception as e:
        print(f"[DISCOVERY] ℹ️ 固定域名已被占用，当前节点为备用节点 ({e})")
        return None, False


# ---------- 别名监听器（故障转移已禁用） ----------
class AliasServiceListener(ServiceListener):
    def add_service(self, zc, type_, name):
        pass
    def remove_service(self, zc, type_, name):
        if name == "campusforum._http._tcp.local.":
            print("[DISCOVERY] 🔄 检测到主节点下线，但自动故障转移已禁用")
    def update_service(self, zc, type_, name):
        pass


async def setup_alias_with_failover(main_zc: Zeroconf, port: int):
    is_leader = False
    alias_zc = None

    async def try_become_leader():
        nonlocal is_leader, alias_zc
        if is_leader:
            return
        zc, success = await async_register_alias_service(port)
        if success:
            is_leader = True
            alias_zc = zc
            print("[DISCOVERY] 👑 当前节点已升级为主节点 (固定域名 campusforum.local)")

    await try_become_leader()

    listener = AliasServiceListener()
    main_zc.add_service_listener(MDNS_SERVICE_TYPE, listener)

    def cleanup():
        nonlocal alias_zc
        if alias_zc:
            alias_zc.close()
        main_zc.remove_service_listener(listener)

    return is_leader, cleanup


# ---------- P2P 节点发现 ----------
async def async_register_p2p_service(port: int, peer_id: str):
    ip = _get_local_ip()
    info = ServiceInfo(
        P2P_SERVICE_TYPE,
        f"{peer_id[-8:]}.{P2P_SERVICE_TYPE}",
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={"peer_id": peer_id},
        server=f"{peer_id[-8:]}.local."
    )
    zc = await trio.to_thread.run_sync(_register_service_sync, info)
    return zc

import queue

class P2PServiceListener(ServiceListener):
    def __init__(self, host, p2p_port, addr_queue):
        self.host = host
        self.p2p_port = p2p_port
        self.addr_queue = addr_queue   # queue.Queue
        self.connected = set()

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if not info or not info.addresses:
            return
        ip = socket.inet_ntoa(info.addresses[0])
        port = info.port
        peer_id = info.properties.get(b"peer_id", b"").decode()
        if port == self.p2p_port and ip == _get_local_ip():
            return
        addr_str = f"/ip4/{ip}/tcp/{port}/p2p/{peer_id}"
        if addr_str not in self.connected:
            try:
                self.addr_queue.put(addr_str)
                self.connected.add(addr_str)
                print(f"[DISCOVERY] 🔍 发现邻居，已加入连接队列: {addr_str}")
            except Exception as e:
                print(f"[DISCOVERY] ⚠️ 无法将地址加入队列: {e}")

    def remove_service(self, zc, type_, name):
        pass

    def update_service(self, zc, type_, name):
        pass