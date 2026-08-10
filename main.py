import argparse
import asyncio
import uvicorn
from config import WEB_PORT, P2P_PORT, AI_MODE
from storage.database import init_db


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

    # 1. 初始化数据库
    init_db()

    # 2. 启动 P2P 网络（先拿到 peer_id）
    host = None
    pubsub = None
    peer_id_str = None
    try:
        from p2p.network import create_host
        from p2p.pubsub import PubSubManager
        host = await create_host(port=args.p2p_port)
        pubsub = PubSubManager(host)
        pubsub.setup()
        peer_id_str = host.get_id().pretty()
        print(f"✅ P2P 节点已启动, PeerID: {peer_id_str}")
    except Exception as e:
        print(f"⚠️ P2P 网络启动失败: {e}")
        print("   将以单机模式运行")

    # 3. 注册唯一的 mDNS 服务 (campusforum-xxxxxx.local)
    from p2p.discovery import async_register_mdns_service, setup_alias_with_failover
    main_zeroconf = None
    unique_name = None
    try:
        main_zeroconf, unique_name = await async_register_mdns_service(
            port=args.port,
            peer_id=peer_id_str
        )
    except Exception as e:
        print(f"⚠️ 唯一 mDNS 注册失败: {e}")
        print(f"  请使用 IP 地址访问: http://localhost:{args.port}")

    # 4. 启动固定域名抢占
    is_leader = False
    alias_cleanup = None
    if main_zeroconf:
        try:
            is_leader, alias_cleanup = await setup_alias_with_failover(main_zeroconf, args.port)
        except Exception as e:
            print(f"⚠️ 固定域名抢占失败: {e}")

    # 5. 将 P2P 对象挂到 FastAPI app 上
    from web.server import app
    app.state.pubsub = pubsub
    app.state.host = host
    app.state.peer_id = peer_id_str

    print("\n按 Ctrl+C 退出")

    # 6. 启动 Web 服务器（最后阻塞）
    config = uvicorn.Config(
        "web.server:app",
        host="0.0.0.0",
        port=args.port,
        log_level="info"
    )
    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        # 清理资源
        if alias_cleanup:
            alias_cleanup()
        if main_zeroconf:
            main_zeroconf.close()
        if host:
            await host.close()
        print("已退出")


if __name__ == "__main__":
    asyncio.run(main())