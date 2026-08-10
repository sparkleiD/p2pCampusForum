// frontend/js/app.js
// 前端主逻辑

const API_BASE = "/api";

// ===== DOM 引用 =====
const postList = document.getElementById("postList");
const postForm = document.getElementById("postForm");
const postContent = document.getElementById("postContent");
const postNickname = document.getElementById("postNickname");
const submitBtn = document.getElementById("submitBtn");
const postCount = document.getElementById("postCount");

// 弹窗
const modal = document.getElementById("postModal");
const modalTitle = document.getElementById("modalTitle");
const modalBody = document.getElementById("modalBody");
const modalClose = document.getElementById("modalClose");

// ===== 工具函数 =====
function formatTime(timestamp) {
    if (!timestamp) return "";
    const date = new Date(timestamp);
    return date.toLocaleString("zh-CN", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    });
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function getStatusText(status) {
    const map = {
        "approved": "已通过",
        "rejected": "未通过",
        "pending": "审核中"
    };
    return map[status] || status;
}

// ===== 渲染帖子列表 =====
function renderPosts(posts) {
    if (!posts || posts.length === 0) {
        postList.innerHTML = `
            <div class="empty-state">
                <span class="emoji">📝</span>
                还没有帖子，快来发第一条吧！
            </div>
        `;
        postCount.textContent = "0 条";
        return;
    }

    let html = "";
    posts.forEach(post => {
        const statusClass = post.status || "pending";
        const statusText = getStatusText(post.status);

        html += `
            <div class="post-card" data-post-id="${post.post_id}">
                <div class="post-meta">
                    <span class="nickname">👤 ${escapeHtml(post.nickname || "匿名")}</span>
                    <span>${formatTime(post.created_at)}</span>
                </div>
                <div class="post-content">${escapeHtml(post.content)}</div>
                <div class="post-footer">
                    <span class="post-status ${statusClass}">${statusText}</span>
                    <span class="post-comment-count">💬 查看详情</span>
                </div>
            </div>
        `;
    });

    postList.innerHTML = html;
    postCount.textContent = `${posts.length} 条`;

    // 绑定点击事件：点击卡片打开详情
    document.querySelectorAll(".post-card").forEach(card => {
        card.addEventListener("click", () => {
            const postId = card.dataset.postId;
            openPostDetail(postId);
        });
    });
}

// ===== 加载帖子列表 =====
async function loadPosts() {
    try {
        const resp = await fetch(`${API_BASE}/posts`);
        const data = await resp.json();
        renderPosts(data.posts || []);
    } catch (err) {
        console.error("加载帖子失败:", err);
        postList.innerHTML = '<div class="empty-state">加载失败，请刷新重试</div>';
    }
}

// ===== 发布帖子 =====
async function submitPost(e) {
    e.preventDefault();

    const content = postContent.value.trim();
    if (!content) {
        alert("请写点内容再发布");
        return;
    }

    const nickname = postNickname.value.trim() || "匿名";

    submitBtn.disabled = true;
    submitBtn.textContent = "发布中...";

    try {
        const formData = new FormData();
        formData.append("content", content);
        formData.append("nickname", nickname);

        const resp = await fetch(`${API_BASE}/posts/`, {
            method: "POST",
            body: formData
        });

        const result = await resp.json();

        if (resp.ok) {
            postContent.value = "";
            postNickname.value = "";
            await loadPosts();
        } else {
            alert(`发布失败: ${result.detail || "未知错误"}`);
        }
    } catch (err) {
        console.error("发布失败:", err);
        alert("发布失败，请检查网络连接");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "发布";
    }
}

// ===== 打开帖子详情 =====
async function openPostDetail(postId) {
    try {
        const resp = await fetch(`${API_BASE}/posts/${postId}`);
        if (!resp.ok) {
            alert("获取帖子详情失败");
            return;
        }

        const data = await resp.json();
        const post = data.post;
        const logs = data.audit_logs || [];

        modalTitle.textContent = `帖子详情`;

        let auditHtml = "";
        if (logs.length > 0) {
            auditHtml = `
                <div class="modal-audit">
                    <strong>AI 审核记录</strong>
                    ${logs.map(log => `
                        <div class="modal-audit-item">
                            [${log.ai_model}] ${log.verdict} - ${log.reason || "无理由"}
                            <span style="color:#a0aec0;font-size:12px;"> (置信度 ${log.confidence}%)</span>
                        </div>
                    `).join("")}
                </div>
            `;
        }

        modalBody.innerHTML = `
            <div class="modal-meta">
                👤 ${escapeHtml(post.nickname || "匿名")} · ${formatTime(post.created_at)}
                <span style="margin-left:12px;">状态: ${getStatusText(post.status)}</span>
            </div>
            <div class="modal-post-content">${escapeHtml(post.content)}</div>
            ${auditHtml}
            <div style="margin-top:12px;font-size:13px;color:#a0aec0;">
                帖子 ID: ${post.post_id}
            </div>
        `;

        modal.classList.remove("hidden");
        document.body.style.overflow = "hidden";

    } catch (err) {
        console.error("加载详情失败:", err);
        alert("加载详情失败");
    }
}

// ===== 关闭弹窗 =====
function closeModal() {
    modal.classList.add("hidden");
    document.body.style.overflow = "";
}

// ===== 事件绑定 =====
postForm.addEventListener("submit", submitPost);

modalClose.addEventListener("click", closeModal);

modal.addEventListener("click", (e) => {
    if (e.target === modal) {
        closeModal();
    }
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        closeModal();
    }
});

// ===== 初始化 =====
document.addEventListener("DOMContentLoaded", () => {
    loadPosts();
});