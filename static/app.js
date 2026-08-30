let token = localStorage.getItem('sases_token');

// ---------- 视图切换 ----------
function switchView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-view="${viewId}"]`).classList.add('active');
}

// ---------- 认证 ----------
function showRegister() {
    document.getElementById('register-section').style.display = 'block';
}

async function login() {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const res = await fetch('/token', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
    });
    if (res.ok) {
        const data = await res.json();
        token = data.access_token;
        localStorage.setItem('sases_token', token);
        showMain();
    } else {
        alert('登录失败');
    }
}

async function register() {
    const username = document.getElementById('reg-username').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const res = await fetch('/register', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, email, password})
    });
    if (res.ok) {
        alert('注册成功，请登录');
        document.getElementById('register-section').style.display = 'none';
    } else {
        alert('注册失败');
    }
}

async function showMain() {
    document.getElementById('auth-section').style.display = 'none';
    document.getElementById('main-section').style.display = 'block';
    switchView('view-chat');
    const res = await fetch('/me', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        document.getElementById('username-display').textContent = data.username;
        document.getElementById('credits-display').textContent = data.credits;
    }
    loadSettings();
    loadLeaderboard();
    loadAssistantUnread();
    loadStats();
}

function logout() {
    localStorage.removeItem('sases_token');
    token = null;
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('main-section').style.display = 'none';
}

// ---------- 聊天 ----------
async function chat() {
    const query = document.getElementById('chat-input').value;
    const res = await fetch('/chat', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({query})
    });
    const data = await res.json();
    document.getElementById('chat-result').textContent = data.answer;
    if (data.deducted) {
        alert(`本次查询已扣除 ${data.deducted} 积分`);
        updateCreditsDisplay();
        loadAssistantUnread();
    }
}

// ---------- 积分流水 ----------
async function showLedger() {
    const res = await fetch('/my_ledger', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        const div = document.getElementById('ledger');
        div.style.display = 'block';
        div.innerHTML = '<h3>积分流水</h3><ul>' + data.ledger.map(item =>
            `<li>${item.amount > 0 ? '+' : ''}${item.amount} 积分 - ${item.reason} (${item.timestamp})</li>`
        ).join('') + '</ul>';
    } else {
        alert('获取积分流水失败');
    }
}

// ---------- 提交种子 ----------
async function submitSeed() {
    if (!localStorage.getItem('seed_risk_dismissed')) {
        const dismiss = confirm('提示：提交的种子将进入 SASES 公共种子池，并被其他用户或系统使用。请勿包含个人隐私信息。\n\n点击“确定”继续，并永久不再提示；点击“取消”返回。');
        if (!dismiss) return;
        localStorage.setItem('seed_risk_dismissed', 'true');
    }
    const description = document.getElementById('seed-desc').value;
    const testcases_str = document.getElementById('seed-testcases').value;
    let test_cases = [];
    try { test_cases = JSON.parse(testcases_str) || []; } catch(e) { test_cases = []; }
    const res = await fetch('/submit_seed', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({description, test_cases})
    });
    if (res.ok) {
        alert('种子已提交');
        loadAssistantUnread();
    } else {
        alert('提交失败');
    }
}

// ---------- 更新积分显示 ----------
async function updateCreditsDisplay() {
    const res = await fetch('/me', { headers: {'Authorization': `Bearer ${token}`} });
    if (res.ok) {
        const data = await res.json();
        document.getElementById('credits-display').textContent = data.credits;
    }
}

// ---------- 排行榜 ----------
async function loadLeaderboard() {
    const res = await fetch('/leaderboard');
    const data = await res.json();
    const list = document.getElementById('leaderboard');
    list.innerHTML = '';
    data.forEach(item => {
        const li = document.createElement('li');
        li.textContent = `${item.username}: ${item.credits} 积分`;
        list.appendChild(li);
    });
}

// ---------- 贡献榜 ----------
async function loadContribLeaderboard() {
    const res = await fetch('/contrib_leaderboard');
    const data = await res.json();
    const div = document.getElementById('discover-content');
    div.innerHTML = '<h3>贡献榜</h3><ul>' + data.map(item =>
        `<li>${item.username}: ${item.score}</li>`
    ).join('') + '</ul>';
}

// ---------- 统计 ----------
async function loadStats() {
    const res = await fetch('/stats');
    const data = await res.json();
    document.getElementById('stats').textContent = JSON.stringify(data, null, 2);
}

function toggleStats() {
    const stats = document.getElementById('stats');
    stats.style.display = stats.style.display === 'none' ? 'block' : 'none';
}

// ---------- 自动授粉设置 ----------
async function loadSettings() {
    const res = await fetch('/me/settings', { headers: {'Authorization': `Bearer ${token}`} });
    if (res.ok) {
        const data = await res.json();
        document.getElementById('auto-pollinate-toggle').checked = data.auto_pollinate_enabled;
    }
}

async function toggleAutoPollinate() {
    const enabled = document.getElementById('auto-pollinate-toggle').checked;
    const res = await fetch('/me/settings', {
        method: 'PATCH',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({auto_pollinate_enabled: enabled})
    });
    if (res.ok) alert('设置已更新'); else alert('设置更新失败');
}

// ---------- SASES 助手 ----------
async function loadAssistantUnread() {
    const res = await fetch('/assistant/messages', { headers: {'Authorization': `Bearer ${token}`} });
    if (res.ok) {
        const data = await res.json();
        const badge = document.getElementById('assistant-unread');
        if (data.unread > 0) {
            badge.textContent = data.unread;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
}

async function showAssistant() {
    const res = await fetch('/assistant/messages', { headers: {'Authorization': `Bearer ${token}`} });
    if (res.ok) {
        const data = await res.json();
        const div = document.getElementById('assistant-messages');
        div.style.display = 'block';
        div.innerHTML = '<h3>SASES助手</h3><ul>' + data.messages.map(msg =>
            `<li><strong>${msg.title}</strong>：${msg.content} <small>(${msg.timestamp})</small></li>`
        ).join('') + '</ul>';

        await fetch('/assistant/read', {
            method: 'POST',
            headers: {'Authorization': `Bearer ${token}`}
        });
        loadAssistantUnread();
    } else {
        alert('获取助手消息失败');
    }
}

// ---------- Harness 工具 ----------
let toolList = [];

async function loadToolList() {
    const res = await fetch('/harness/tools');
    if (res.ok) {
        toolList = await res.json();
        const select = document.getElementById('tool-select');
        select.innerHTML = '';
        toolList.forEach(tool => {
            const opt = document.createElement('option');
            opt.value = tool.module_id;
            opt.textContent = `${tool.name} (${tool.module_id})`;
            select.appendChild(opt);
        });
    } else {
        alert('获取工具列表失败');
    }
}

function toggleHarnessPanel() {
    const panel = document.getElementById('harness-panel');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        loadToolList();
    } else {
        panel.style.display = 'none';
    }
}

async function invokeTool() {
    const moduleId = document.getElementById('tool-select').value;
    const paramsText = document.getElementById('tool-params').value.trim();
    let params = {};
    if (paramsText) {
        try { params = JSON.parse(paramsText); } catch(e) { alert('参数 JSON 格式错误'); return; }
    }
    const res = await fetch('/harness/invoke', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ module_id: moduleId, params })
    });
    const data = await res.json();
    document.getElementById('tool-result').textContent = JSON.stringify(data, null, 2);
}

// ---------- 空间节点 ----------
let nodeList = [];

async function loadNodeList() {
    const res = await fetch('/space/nodes');
    if (res.ok) {
        nodeList = await res.json();
        const ul = document.getElementById('node-list');
        ul.innerHTML = '';
        nodeList.forEach(node => {
            const li = document.createElement('li');
            li.style.display = 'flex';
            li.style.justifyContent = 'space-between';
            li.style.alignItems = 'center';

            const statusText = node.status || 'unknown';
            const statusColor = statusText === 'online' ? 'green' : statusText === 'offline' ? 'red' : 'gray';
            const statusHtml = `<span style="color:${statusColor}; margin-right:5px;">●</span> ${statusText}`;

            li.innerHTML = `<span>${statusHtml} ${node.name} (${node.node_id})</span>`;
            const btn = document.createElement('button');
            btn.textContent = '调用';
            btn.onclick = () => invokeNode(node.node_id);
            li.appendChild(btn);
            ul.appendChild(li);
        });
    } else {
        alert('获取节点列表失败');
    }
}

function toggleNodePanel() {
    const panel = document.getElementById('node-panel');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        loadNodeList();
    } else {
        panel.style.display = 'none';
    }
}

async function invokeNode(nodeId) {
    if (!token) {
        alert('请先登录');
        return;
    }

    const paramsText = prompt(`输入调用节点 ${nodeId} 的参数 JSON（留空表示 {}）：`);
    let params = {};
    if (paramsText && paramsText.trim() !== '') {
        try {
            params = JSON.parse(paramsText);
            if (typeof params !== 'object' || Array.isArray(params)) {
                alert('参数必须是 JSON 对象，例如 {"key":"value"}');
                return;
            }
        } catch (e) {
            alert('参数 JSON 格式错误');
            return;
        }
    }

    if (!nodeId || typeof nodeId !== 'string') {
        alert('节点 ID 无效');
        return;
    }

    try {
        const res = await fetch('/space/invoke', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ node_id: nodeId, params: params })
        });

        if (res.status === 401) {
            alert('登录已过期，请重新登录');
            logout();
            return;
        }

        const data = await res.json();
        document.getElementById('node-invoke-result').textContent = JSON.stringify(data, null, 2);
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
}

// ---------- 知识库导出 ----------
async function exportKnowledgeBase() {
    const res = await fetch('/kb/export', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'success_kb.json';
        a.click();
        URL.revokeObjectURL(url);
    } else {
        alert('导出知识库失败');
    }
}

// ---------- 通用设置 ----------
async function loadGeneralSettings() {
    const res = await fetch('/me/settings/all', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        document.getElementById('general-settings-json').value = JSON.stringify(data, null, 2);
    }
}

function toggleGeneralSettings() {
    const panel = document.getElementById('general-settings-panel');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        loadGeneralSettings();
    } else {
        panel.style.display = 'none';
    }
}

async function saveGeneralSettings() {
    const text = document.getElementById('general-settings-json').value.trim();
    let settings;
    try { settings = JSON.parse(text); } catch(e) { alert('设置 JSON 格式错误'); return; }
    const res = await fetch('/me/settings/all', {
        method: 'PATCH',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({settings})
    });
    if (res.ok) {
        alert('设置已保存');
    } else {
        alert('保存设置失败');
    }
}

// ---------- API Key 管理 ----------
async function toggleApiKeyPanel() {
    const panel = document.getElementById('api-key-panel');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        loadApiKeys();
    } else {
        panel.style.display = 'none';
    }
}

async function loadApiKeys() {
    const res = await fetch('/api_keys', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const keys = await res.json();
        const ul = document.getElementById('api-key-list');
        ul.innerHTML = '';
        keys.forEach(k => {
            const li = document.createElement('li');
            li.style.display = 'flex';
            li.style.justifyContent = 'space-between';
            li.style.alignItems = 'center';
            li.innerHTML = `<span>${k.provider} - ${k.masked_key} (优先级:${k.priority})</span>`;
            const btnPriority = document.createElement('button');
            btnPriority.textContent = '设优先';
            btnPriority.onclick = () => setApiKeyPriority(k.id);
            const btnDel = document.createElement('button');
            btnDel.textContent = '删除';
            btnDel.onclick = () => deleteApiKey(k.id);
            li.appendChild(btnPriority);
            li.appendChild(btnDel);
            ul.appendChild(li);
        });
    } else {
        alert('获取 API Key 列表失败');
    }
}

async function addApiKey() {
    const provider = document.getElementById('api-key-provider').value;
    const key = document.getElementById('api-key-value').value.trim();
    const priority = parseInt(document.getElementById('api-key-priority').value) || 0;
    if (!provider || !key) { alert('请填写提供商和 API Key'); return; }
    const res = await fetch('/api_keys', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({provider, key, priority})
    });
    if (res.ok) {
        alert('API Key 已添加');
        loadApiKeys();
    } else {
        alert('添加失败');
    }
}

async function deleteApiKey(id) {
    if (!confirm('确认删除该 API Key？')) return;
    const res = await fetch(`/api_keys/${id}`, {
        method: 'DELETE',
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        alert('已删除');
        loadApiKeys();
    } else {
        alert('删除失败');
    }
}

async function setApiKeyPriority(id) {
    const priority = prompt('输入新的优先级（数字越大越优先）：');
    if (!priority) return;
    const res = await fetch('/api_keys/priority', {
        method: 'PATCH',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({key_id: id, priority: parseInt(priority)})
    });
    if (res.ok) {
        alert('优先级已更新');
        loadApiKeys();
    } else {
        alert('更新失败');
    }
}

// 自动进入主界面
if (token) {
    showMain();
}