import argparse
import trio
import queue
from hypercorn.trio import serve
from hypercorn.config import Config as HyperConfig
from multiaddr import Multiaddr

from config import WEB_PORT, P2P_PORT, AI_MODE
from storage.database import init_db

# import logging
# logging.basicConfig(level=logging.DEBUG)

async def run_p2p(host, listen_addr,ready_event): # listen_addr: 在 #3 中创建的 Multiaddr 对象
    """P2P 网络任务（在 Trio Nursery 中运行）"""
    async with host.run(listen_addrs=[listen_addr]):
        # 打印实际监听的地址（调试用）
        print(f"[MAIN] 🔍 P2P 实际监听地址: {host.get_addrs()}")
        # 设置 ready_event，通知主协程 P2P 已启动
        ready_event.set()
        # 保持运行，直到被取消
        await trio.sleep_forever()


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
    pubsub = PubSubManager(host) # 内部引用host建立关联
    pubsub.setup()

    # 注册消息处理器（通过路由器）
    route_callback = pubsub.setup_router()

    # 5. 注册 mDNS 服务
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
    stop_event = trio.Event()   # 改动：退出标志

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

    # 6. 启动 P2P mDNS 节点发现
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

    # 9. 定义连接消费协程，从队列中取出地址并建立 P2P 连接
    async def connect_loop():

        await host_ready.wait()  # 等待退出信号

        if addr_queue is None:
            return
        while not stop_event.is_set():   # 改动：检查退出标志
            try:
                # 使用带超时的 get，每 0.5 秒检查一次停止标志
                # 从队列中获取一个地址字符串（阻塞直到有数据或超时）
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
                # 此时 peer_id_str 示例= "12D3KooWRNPgPpAAAr4fswqAFDUVm3wuUq7QhNmerFDk5tWAamHu"

                from libp2p.peer.id import ID
                from libp2p.peer.peerinfo import PeerInfo
                peer_id = ID.from_base58(peer_id_str)
                addr = Multiaddr(addr_str)

                addr_without_p2p = Multiaddr(addr_str.split('/p2p/')[0])
                peer_info = PeerInfo(peer_id, [addr_without_p2p])

                await host.connect(peer_info)
                print(f"[MAIN] 🔗 P2P 已连接: {addr_str}")
            except Exception as e:
                import traceback
                print(f"[MAIN] ⚠️ 连接失败 {addr_str}: {e}")
                traceback.print_exc()   # 打印完整异常链

    # 10. 使用 Trio Nursery 同时运行 P2P 和 Web
    try:
        async with trio.open_nursery() as nursery:

            host_ready = trio.Event()  # 用于等待 P2P 启动完成
            # 启动 P2P 任务
            nursery.start_soon(run_p2p, host, listen_addr, host_ready)
            # 启动 Web 服务
            nursery.start_soon(serve, app, hyper_config)
            # 启动连接消费任务
            if addr_queue is not None:
                nursery.start_soon(connect_loop)
            # 启动 P2P 消息接收任务
            nursery.start_soon(pubsub.run_receiver, route_callback)
    finally:
        # 设置退出标志，让 connect_loop 退出
        stop_event.set()   # 改动
        # 清理资源
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