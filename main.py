import argparse
import trio
import queue
from hypercorn.trio import serve
from hypercorn.config import Config as HyperConfig
from multiaddr import Multiaddr

from config import WEB_PORT, P2P_PORT, AI_MODE
from storage.database import init_db

# 新增导入（若导入失败，请手动定义 background_trio_service）
try:
    from libp2p.tools.anyio_service import background_trio_service
except ImportError:
    # 如果 libp2p 版本较旧，手动实现一个简单的异步上下文管理器
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def background_trio_service(obj):
        async with obj:
            yield

# import logging
# logging.basicConfig(level=logging.DEBUG)

async def main():
    parser = argparse.ArgumentParser(description="去中心化校园论坛节点")
    parser.add_argument("--ai-mode", type=str, default=AI_MODE,
                        choices=["api", "local"],
                        help=f"AI 模式(默认 {AI_MODE})")
    parser.add_argument("--port", type=int, default=WEB_PORT,
                        help=f"Web 端口(默认 {WEB_PORT})")
    parser.add_argument("--p2p-port", type=int, default=P2P_PORT,
                        help=f"P2P 端口(默认 {P2P_PORT})")
    args = parser.parse_args()

    print(f"""
========================================
  去中心化校园论坛 v1.0
========================================
  AI 模式: {args.ai_mode}
  Web 端口: {args.port}
  P2P 端口: {args.p2p_port}
========================================
    """)

    # 1. 初始化数据库（同步，但在 Trio 中可安全调用）
    init_db()

    # 2. 创建 P2P Host（不启动）
    from p2p.network import create_host
    host = await create_host()
    peer_id_str = host.get_id().pretty()
    print(f"[MAIN] ✅ P2P 节点已创建, PeerID: {peer_id_str}")

    # 3. 构造监听地址（P2P 端口从命令行读取）
    listen_addr = Multiaddr(f"/ip4/0.0.0.0/tcp/{args.p2p_port}")

    # 4. 初始化 PubSub
    from p2p.pubsub import PubSubManager
    pubsub = PubSubManager(host)    # 内部引用 host
    pubsub.setup()                  # 创建 GossipSub 和 Pubsub 实例

    # 注册消息处理器（通过路由器）
    route_callback = pubsub.setup_router()

    # 5. 注册 mDNS 服务（用于 Web 页面发现，保留原有代码）
    from p2p.discovery import (
        async_register_mdns_service,
        setup_alias_with_failover,
        async_register_p2p_service,
        P2PServiceListener,
        P2P_SERVICE_TYPE
    )
    from zeroconf import ServiceBrowser

    main_zeroconf = None
    unique_name = None
    alias_cleanup = None
    p2p_zeroconf = None
    p2p_browser = None
    addr_queue = None

    try:
        main_zeroconf, unique_name = await async_register_mdns_service(
            port=args.port,
            peer_id=peer_id_str
        )
    except Exception as e:
        print(f"[MAIN] ⚠️ 唯一 mDNS 注册失败: {e}")

    if main_zeroconf:
        try:
            is_leader, alias_cleanup = await setup_alias_with_failover(
                main_zeroconf, args.port
            )
        except Exception as e:
            print(f"[MAIN] ⚠️ 固定域名抢占失败: {e}")

    # 6. 启动 P2P mDNS 节点发现（用于自动发现其他节点）
    try:
        p2p_zeroconf = await async_register_p2p_service(args.p2p_port, peer_id_str)
        addr_queue = queue.Queue()
        listener = P2PServiceListener(host, args.p2p_port, addr_queue)
        p2p_browser = ServiceBrowser(p2p_zeroconf, P2P_SERVICE_TYPE, listener)
        print("[MAIN] ✅ P2P mDNS 发现已启动")
    except Exception as e:
        print(f"[MAIN] ⚠️ P2P 发现启动失败: {e}")

    # 7. 将 P2P 对象挂到 FastAPI app 上
    from web.server import app
    app.state.pubsub = pubsub
    app.state.host = host
    app.state.peer_id = peer_id_str

    # 8. 配置 Hypercorn（Trio 后端）
    hyper_config = HyperConfig()
    hyper_config.bind = [f"0.0.0.0:{args.port}"]
    hyper_config.use_reloader = False

    print(f"\n[MAIN] 🌐 Web 服务运行在 http://localhost:{args.port}")
    print("[MAIN] 🕒 按 Ctrl+C 退出")

    # 9. 定义连接消费协程（从队列中取出地址并建立 P2P 连接）
    async def connect_loop():
        """从 mDNS 发现队列中获取 peer 地址并连接"""
        if addr_queue is None:
            return
        # 使用 trio 的取消作用域，在外部取消时自动退出
        while True:
            try:
                # 阻塞获取，使用 to_thread 避免阻塞事件循环
                addr_str = await trio.to_thread.run_sync(
                    lambda: addr_queue.get(timeout=0.5)
                )
                print(f"[MAIN] 🐞 从队列取出的地址: {addr_str}")
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[MAIN] ⚠️ 队列获取错误: {e}")
                break

            try:
                # 从 addr_str 中提取 peer_id
                if '/p2p/' not in addr_str:
                    print(f"[MAIN] ⚠️ 无效地址格式（缺少 /p2p/）: {addr_str}")
                    continue
                peer_id_str = addr_str.split('/p2p/')[1]

                from libp2p.peer.id import ID
                from libp2p.peer.peerinfo import PeerInfo
                peer_id = ID.from_base58(peer_id_str)
                addr_without_p2p = Multiaddr(addr_str.split('/p2p/')[0])
                peer_info = PeerInfo(peer_id, [addr_without_p2p])

                await host.connect(peer_info)
                print(f"[MAIN] 🔗 P2P 已连接: {addr_str}")
            except Exception as e:
                import traceback
                print(f"[MAIN] ⚠️ 连接失败 {addr_str}: {e}")
                traceback.print_exc()

    # 10. 使用 Trio Nursery 运行所有服务
    try:
        async with trio.open_nursery() as nursery:
            # 启动 P2P 主任务（包含 Host 监听、PubSub 服务、消息接收、连接消费）
            async def p2p_main():
                # 用 host.run() 启动监听
                async with host.run(listen_addrs=[listen_addr]):
                    # 启动 PubSub 和 GossipSub 的后台服务
                    async with background_trio_service(pubsub._pubsub):
                        async with background_trio_service(pubsub._gossipsub):
                            print("[MAIN] ✅ P2P 服务已完全启动（GossipSub 已运行）")
                            # 在一个内层 nursery 中启动消息接收和连接任务
                            async with trio.open_nursery() as inner:
                                # 启动消息接收循环
                                inner.start_soon(pubsub.run_receiver, route_callback)
                                # 启动连接消费任务（如果有队列）
                                if addr_queue is not None:
                                    inner.start_soon(connect_loop)
                                # 保持内层 nursery 存活
                                await trio.sleep_forever()

            # 启动 P2P 主任务
            nursery.start_soon(p2p_main)

            # 启动 Web 服务
            nursery.start_soon(serve, app, hyper_config)

            # 所有任务会在 cancel scope 取消时自动退出
            # 等待直到被中断（Ctrl+C）
            await trio.sleep_forever()

    finally:
        # 清理 mDNS 等服务
        if alias_cleanup:
            alias_cleanup()
        if main_zeroconf:
            main_zeroconf.close()
        if p2p_browser:
            p2p_browser.cancel()
        if p2p_zeroconf:
            p2p_zeroconf.close()
        print("[MAIN] ✅ 已退出")


if __name__ == "__main__":
    trio.run(main)