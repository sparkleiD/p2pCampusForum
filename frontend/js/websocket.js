// frontend/js/websocket.js
// WebSocket 客户端

let ws = null;
let reconnectTimer = null;
const RECONNECT_DELAY = 3000;

function connectWebSocket() {
    // 构建 WebSocket URL
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log("[WebSocket] 已连接");
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (err) {
                console.error("[WebSocket] 消息解析失败:", err);
            }
        };

        ws.onclose = () => {
            console.log("[WebSocket] 已断开, 尝试重连...");
            scheduleReconnect();
        };

        ws.onerror = (err) => {
            console.error("[WebSocket] 错误:", err);
            ws.close();
        };

    } catch (err) {
        console.error("[WebSocket] 连接失败:", err);
        scheduleReconnect();
    }
}

function scheduleReconnect() {
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectWebSocket();
    }, RECONNECT_DELAY);
}

function handleWebSocketMessage(data) {
    const type = data.type;

    if (type === "new_post") {
        console.log("[WebSocket] 收到新帖子:", data.data);
        // 刷新帖子列表
        if (typeof loadPosts === "function") {
            loadPosts();
        }
    } else if (type === "new_comment") {
        console.log("[WebSocket] 收到新评论:", data.data);
        // 如果当前弹窗打开且是同一帖子, 刷新详情
        // 简单处理: 不自动刷新详情, 让用户手动刷新
    } else if (type === "ping") {
        // 心跳响应, 忽略
    } else {
        console.log("[WebSocket] 未知消息类型:", type, data);
    }
}

// 发送心跳 (保持连接活跃)
function sendHeartbeat() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
    }
}

// 页面加载时自动连接
document.addEventListener("DOMContentLoaded", () => {
    connectWebSocket();

    // 每 30 秒发送一次心跳
    setInterval(sendHeartbeat, 30000);
});

// 页面关闭前断开连接
window.addEventListener("beforeunload", () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
    }
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
});

console.log("[WebSocket] 客户端已加载");