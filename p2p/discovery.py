import socket
import asyncio
import uuid
from zeroconf import ServiceInfo, Zeroconf, ServiceListener
from config import MDNS_SERVICE_NAME, MDNS_SERVICE_TYPE, WEB_PORT


# ---------- 工具函数 ----------
def _get_local_ip():
    """获取本机有效的局域网 IPv4 地址（避免返回 127.0.0.1）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


# ---------- 唯一服务注册（每个节点独立） ----------
async def async_register_mdns_service(port: int = None, service_name: str = None, peer_id: str = None):
    """
    注册一个带唯一后缀的服务实例，例如 campusforum-a3f9c2.local

    :param port:  Web 服务端口
    :param service_name: 自定义服务名（若 None 则自动生成）
    :param peer_id: P2P 节点 ID，用于生成唯一后缀
    
    :return: (Zeroconf 实例, 最终注册的服务名)
    """
    if port is None:
        port = WEB_PORT

    # 构造唯一服务名
    if service_name is None:
        if peer_id:
            suffix = peer_id[-6:] if len(peer_id) >= 6 else peer_id
            service_name = f"{MDNS_SERVICE_NAME}-{suffix}"
        else:
            service_name = f"{MDNS_SERVICE_NAME}-{uuid.uuid4().hex[:6]}"

    ip = _get_local_ip()
    info = ServiceInfo(
        MDNS_SERVICE_TYPE,                       # "_http._tcp.local."
        f"{service_name}.{MDNS_SERVICE_TYPE}",  # "campusforum-a3f9c2._http._tcp.local."
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={"path": "/", "peer_id": peer_id or ""},
        server=f"{service_name}.local."          # 关键：确保 A 记录正确绑定
    )

    zeroconf = Zeroconf()
    await zeroconf.async_register_service(info)
    print(f"✅ 唯一服务已注册: http://{service_name}.local:{port}")
    print(f"   本机 IP: {ip}")
    return zeroconf, service_name


# ---------- 固定别名抢占（仅主节点） ----------
async def async_register_alias_service(port: int = None):
    """
    尝试注册固定域名 campusforum.local（竞争主节点）

    :param port: Web 端口
    
    :return: (Zeroconf 实例, 是否成功)
    """
    if port is None:
        port = WEB_PORT

    ip = _get_local_ip()
    alias_name = "campusforum"  # 固定短域名，不带后缀

    info = ServiceInfo(
        MDNS_SERVICE_TYPE,
        f"{alias_name}.{MDNS_SERVICE_TYPE}",  # campusforum._http._tcp.local.
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={"path": "/", "is_leader": "true"},
        server=f"{alias_name}.local."          # 绑定 A 记录到 campusforum.local.
    )

    zeroconf = Zeroconf()
    try:
        await zeroconf.async_register_service(info)
        print(f"👑 成功抢占固定域名: http://{alias_name}.local:{port} (当前为主节点)")
        return zeroconf, True
    except Exception as e:
        # 名字冲突，说明已有主节点
        print(f"ℹ️ 固定域名已被占用，当前节点为备用节点 ({e})")
        zeroconf.close()
        return None, False


# ---------- 监听器：检测主节点消失 ----------
class AliasServiceListener(ServiceListener):
    """监听 campusforum.local 的消失，触发抢占回调"""
    def __init__(self, on_alias_lost_callback):
        self.callback = on_alias_lost_callback

    def add_service(self, zeroconf, service_type, name):
        # 当服务出现时，不做特殊处理
        pass

    def remove_service(self, zeroconf, service_type, name):
        # 当固定域名被移除（主节点下线）时触发
        if name == "campusforum._http._tcp.local.":
            print("🔄 检测到主节点下线，触发抢占回调...")
            asyncio.create_task(self.callback())

    def update_service(self, zeroconf, service_type, name):
        pass


# ---------- 封装：启动别名管理（抢占+故障转移） ----------
async def setup_alias_with_failover(main_zeroconf: Zeroconf, port: int):
    """
    启动固定域名 campusforum.local 的抢占和故障转移
    :param main_zeroconf: 主 Zeroconf 实例（用于监听）
    :param port: Web 端口
    :return: (is_leader, cleanup_function)
    """
    is_leader = False
    alias_zeroconf = None

    async def try_become_leader():
        nonlocal is_leader, alias_zeroconf
        if is_leader:
            return
        zc, success = await async_register_alias_service(port=port)
        if success:
            is_leader = True
            alias_zeroconf = zc
            print("👑 当前节点已升级为主节点 (固定域名 campusforum.local)")

    async def on_leader_lost():
        # 当主节点消失时，尝试抢占
        await try_become_leader()

    # 1. 首次抢占
    await try_become_leader()

    # 2. 注册监听器
    listener = AliasServiceListener(on_leader_lost)
    main_zeroconf.add_service_listener("_http._tcp.local.", listener)

    # 3. 返回清理函数
    def cleanup():
        nonlocal alias_zeroconf
        if alias_zeroconf:
            alias_zeroconf.close()
        main_zeroconf.remove_service_listener(listener)

    return is_leader, cleanup


# ---------- 同步兼容（可选） ----------
def register_mdns_service(port: int = None, service_name: str = None, peer_id: str = None):
    """同步版本（兼容旧调用，不建议使用）"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(async_register_mdns_service(port, service_name, peer_id))


def unregister_mdns_service(zeroconf: Zeroconf):
    if zeroconf:
        zeroconf.unregister_all_services()
        zeroconf.close()