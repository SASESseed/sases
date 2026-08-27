let token = localStorage.getItem('sases_token');
if (!token) {
    window.location.href = '/static/index.html';
}

const currentConversation = 'assistant';  // 目前固定为SASES助手
let chatHistory = JSON.parse(localStorage.getItem('sases_chat_history')) || {};
if (!chatHistory[currentConversation]) {
    chatHistory[currentConversation] = [];
}

// ---------- 工具函数 ----------
function saveHistory() {
    localStorage.setItem('sases_chat_history', JSON.stringify(chatHistory));
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', { hour12: false });
}

// ---------- 加载会话列表 ----------
async function loadConversations() {
    const list = document.getElementById('conversation-list');
    list.innerHTML = '';

    // 固定显示 SASES 助手会话
    const item = document.createElement('div');
    item.className = 'conversation-item active';
    item.innerHTML = `
        <div class="conversation-avatar">S</div>
        <div class="conversation-info">
            <div class="conversation-name">SASES助手</div>
            <div class="conversation-last">系统通知与AI对话</div>
        </div>
        <span class="unread-badge" id="unread-badge" style="display:none;"></span>
    `;
    item.onclick = () => switchConversation('assistant');
    list.appendChild(item);

    updateUnreadBadge();
}

// 更新未读消息提示
async function updateUnreadBadge() {
    try {
        const res = await fetch('/assistant/messages', {
            headers: {'Authorization': `Bearer ${token}`}
        });
        if (res.ok) {
            const data = await res.json();
            const badge = document.getElementById('unread-badge');
            if (data.unread > 0) {
                badge.textContent = data.unread;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    } catch(e) {
        console.error('获取未读消息失败', e);
    }
}

// ---------- 切换会话 ----------
async function switchConversation(conversationId) {
    document.getElementById('chat-title').textContent = 'SASES助手';
    renderMessages();
    // 标记系统消息已读
    try {
        await fetch('/assistant/read', {
            method: 'POST',
            headers: {'Authorization': `Bearer ${token}`}
        });
        updateUnreadBadge();
    } catch(e) {
        console.error('标记已读失败', e);
    }
}

// ---------- 渲染消息列表 ----------
async function renderMessages() {
    const messageList = document.getElementById('message-list');
    messageList.innerHTML = '';

    // 加载本地聊天历史
    const localMessages = chatHistory[currentConversation] || [];

    // 加载系统消息
    let systemMessages = [];
    try {
        const res = await fetch('/assistant/messages', {
            headers: {'Authorization': `Bearer ${token}`}
        });
        if (res.ok) {
            const data = await res.json();
            systemMessages = data.messages.map(msg => ({
                sender: 'assistant',
                text: msg.content,
                timestamp: msg.timestamp,
                title: msg.title
            }));
        }
    } catch(e) {
        console.error('获取系统消息失败', e);
    }

    // 合并消息，按时间排序
    const allMessages = [
        ...systemMessages.map(m => ({...m, source: 'system'})),
        ...localMessages.map(m => ({...m, source: 'local'}))
    ];

    allMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    if (allMessages.length === 0) {
        messageList.innerHTML = '<div style="text-align:center;color:#999;margin-top:30px;">暂无消息，发送一条消息开始对话吧。</div>';
        return;
    }

    allMessages.forEach(msg => {
        const bubble = document.createElement('div');
        if (msg.sender === 'user') {
            bubble.className = 'message-bubble sent';
        } else {
            bubble.className = 'message-bubble received';
        }

        let content = msg.text;
        if (msg.title && msg.title !== 'SASES助手') {
            content = `<strong>${msg.title}</strong>：${msg.text}`;
        }

        bubble.innerHTML = `${content}<div class="message-time">${formatTime(msg.timestamp)}</div>`;
        messageList.appendChild(bubble);
    });

    messageList.scrollTop = messageList.scrollHeight;
}

// ---------- 发送消息 ----------
async function sendMessage() {
    const input = document.getElementById('message-input');
    const text = input.value.trim();
    if (!text) return;

    // 添加用户消息到本地历史
    chatHistory[currentConversation].push({
        sender: 'user',
        text: text,
        timestamp: new Date().toISOString()
    });
    saveHistory();
    input.value = '';
    renderMessages();

    // 调用后端 /chat 接口
    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({query: text})
        });
        const data = await res.json();

        // 添加助手回复到本地历史
        chatHistory[currentConversation].push({
            sender: 'assistant',
            text: data.answer || '（无回复）',
            timestamp: new Date().toISOString()
        });
        saveHistory();
        renderMessages();
    } catch(e) {
        chatHistory[currentConversation].push({
            sender: 'assistant',
            text: '发送失败：' + e.message,
            timestamp: new Date().toISOString()
        });
        saveHistory();
        renderMessages();
    }
}

// ---------- 退出登录 ----------
function logout() {
    localStorage.removeItem('sases_token');
    window.location.href = '/static/index.html';
}

// ---------- 初始化 ----------
loadConversations();
switchConversation(currentConversation);

// 每30秒刷新未读消息提示
setInterval(updateUnreadBadge, 30000);