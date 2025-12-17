let currentConvoId = null;
let pollTimer = null;
let searchTimer = null;
let isSending = false;

// ---------- CSRF (cookie 기반) ----------
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return null;
}

function csrfHeader() {
    const token = getCookie("csrftoken");
    return token ? { "X-CSRFToken": token } : {};
}

// ---------- HTTP helpers ----------
async function apiGet(url) {
    const res = await fetch(url, { credentials: "same-origin" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

async function apiPost(url, body) {
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...csrfHeader() },
        credentials: "same-origin",
        body: JSON.stringify(body ?? {}),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

async function apiPatch(url, body) {
    const res = await fetch(url, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...csrfHeader() },
        credentials: "same-origin",
        body: JSON.stringify(body ?? {}),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

// ---------- Utils ----------
function escapeHtml(s) {
    return String(s)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function linkifySafe(text) {
    const escaped = escapeHtml(text);
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return escaped.replace(urlRegex, (url) => {
        return `<a href="${url}" target="_blank" rel="noopener">${url}</a>`;
    });
}

function clearSearchDropdown() {
    const box = document.getElementById("userSearchResults");
    if (box) box.innerHTML = "";
}

// ---------- Conversations ----------
async function loadConversations() {
    const list = await apiGet("/api/conversations/");
    const el = document.getElementById("convoList");
    if (!el) return;

    el.innerHTML = "";

    list.forEach((c) => {
        const div = document.createElement("div");
        div.className = "item" + (c.unread_count > 0 ? " unread" : "");
        div.onclick = () => selectConversation(c.id, c.other_user?.username);

        const left = document.createElement("div");
        left.innerHTML = `
      <div class="name">${escapeHtml(c.other_user?.username ?? "Unknown")}</div>
      <div class="meta">${escapeHtml(c.last_message?.body ?? "")}</div>
    `;

        const right = document.createElement("div");
        right.innerHTML = c.unread_count > 0 ? `<span class="badge">${c.unread_count}</span>` : "";

        div.appendChild(left);
        div.appendChild(right);
        el.appendChild(div);
    });
}

// ---------- Messages ----------
async function loadMessages(convoId) {
    const data = await apiGet(`/api/conversations/${convoId}/messages/`);
    const msgs = data.results || [];
    const box = document.getElementById("messages");
    if (!box) return;

    box.innerHTML = "";

    // 오래된 → 최신 순으로 보여주기 위해 reverse
    msgs.reverse().forEach((m) => {
        const div = document.createElement("div");
        const isMe = m.sender?.username === window.ME;
        div.className = "msg " + (isMe ? "me" : "other");

        div.innerHTML = `
      <div>${linkifySafe(m.body)}</div>
      <div class="meta">${escapeHtml(m.sender?.username ?? "")} • ${escapeHtml(m.created_at)}</div>
    `;
        box.appendChild(div);
    });

    // 읽음 처리
    await apiPatch(`/api/conversations/${convoId}/read/`, {});
}

async function selectConversation(convoId, username) {
    currentConvoId = convoId;

    const titleEl = document.getElementById("chatTitle");
    if (titleEl) {
        titleEl.textContent = username ? `${username}` : `Conversation #${convoId}`;
    }

    await loadMessages(convoId);
    await loadConversations();

    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
        if (!currentConvoId) return;
        try {
            await loadMessages(currentConvoId);
            await loadConversations();
        } catch (e) {
            console.error(e);
        }
    }, 2500);
}

async function sendMessage() {
    if (isSending) return;

    if (!currentConvoId) {
        alert("대화방을 선택하세요.");
        return;
    }

    const bodyEl = document.getElementById("msgBody");
    if (!bodyEl) return;

    const body = bodyEl.value.trim();
    if (!body) return;

    const btnSend = document.getElementById("btnSend");

    try {
        isSending = true;
        if (btnSend) btnSend.disabled = true;

        await apiPost(`/api/conversations/${currentConvoId}/messages/`, { body });

        bodyEl.value = "";
        await loadMessages(currentConvoId);
        await loadConversations();
    } finally {
        isSending = false;
        if (btnSend) btnSend.disabled = false;
    }
}

function bindEnterToSend() {
    const bodyEl = document.getElementById("msgBody");
    if (!bodyEl) return;

    bodyEl.addEventListener("keydown", async (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            try {
                await sendMessage();
            } catch (err) {
                console.error(err);
                alert("메시지 전송 실패: " + err.message);
            }
        }
    });
}

// ---------- User Search (New DM) ----------
async function searchUsers(query) {
    const q = (query || "").trim();
    if (q.length < 2) return [];
    return await apiGet(`/api/users/?query=${encodeURIComponent(q)}`);
}

function renderUserResults(users) {
    const box = document.getElementById("userSearchResults");
    if (!box) return;

    box.innerHTML = "";

    if (!users.length) {
        box.innerHTML = `<div class="search-empty">검색 결과가 없습니다</div>`;
        return;
    }

    users.forEach((u) => {
        const div = document.createElement("div");
        div.className = "search-item";

        const initial = (u.username || "?").charAt(0).toUpperCase();

        div.innerHTML = `
      <div class="search-avatar">${escapeHtml(initial)}</div>
      <div class="search-username">${escapeHtml(u.username)}</div>
    `;

        div.onclick = async () => {
            try {
                const res = await apiPost("/api/conversations/", { other_user_id: u.id });

                await loadConversations();
                await selectConversation(res.id, u.username);

                const input = document.getElementById("userSearch");
                if (input) input.value = "";
                box.innerHTML = "";
            } catch (e) {
                console.error(e);
                alert("대화 생성 실패: " + e.message);
            }
        };

        box.appendChild(div);
    });
}

function bindUserSearch() {
    const input = document.getElementById("userSearch");
    if (!input) return;

    input.addEventListener("input", () => {
        const q = input.value;

        if (searchTimer) clearTimeout(searchTimer);
        searchTimer = setTimeout(async () => {
            try {
                const trimmed = (q || "").trim();
                if (trimmed.length < 2) {
                    clearSearchDropdown();
                    return;
                }
                const users = await searchUsers(trimmed);
                renderUserResults(users);
            } catch (e) {
                console.error(e);
            }
        }, 250);
    });

    // ESC로 닫기
    input.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            clearSearchDropdown();
            input.blur();
        }
    });
}

// 바깥 클릭 시 드롭다운 닫기
function bindOutsideClickToCloseSearch() {
    document.addEventListener("click", (e) => {
        const wrap = document.querySelector(".search-box");
        if (!wrap) return;
        if (!wrap.contains(e.target)) clearSearchDropdown();
    });
}

// ---------- Bootstrap ----------
async function bootstrap() {
    // 내 username 설정(상단 영역에서 파싱)
    const meText = document.querySelector(".me")?.textContent?.trim() || "";
    window.ME = meText.split(/\s+/)[0];

    const btnSend = document.getElementById("btnSend");
    if (btnSend) btnSend.onclick = () => sendMessage().catch((e) => alert("전송 실패: " + e.message));

    bindEnterToSend();
    bindUserSearch();
    bindOutsideClickToCloseSearch();

    await loadConversations();
}

bootstrap().catch((e) => {
    console.error(e);
    alert("초기 로딩 실패: " + e.message);
});