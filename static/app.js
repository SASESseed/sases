// 确保页面加载时只显示聊天视图
document.addEventListener('DOMContentLoaded', function() {
    const views = document.querySelectorAll('.view');
    views.forEach(v => v.classList.remove('active'));
    const chatView = document.getElementById('view-chat');
    if (chatView) chatView.classList.add('active');
});

let token = localStorage.getItem('sases_token');
let selectedImageBase64 = null;
let selectedAudioBase64 = null;
let selectedVideoBase64 = null;

const TOOL_EXAMPLES = {
    'unit-converter': '{"celsius": 30}',
    'calculator': '{"expression": "2+3*4"}',
    'text-stats': '{"text": "Hello world. Hello again."}',
    'json-formatter': '{"json_string": "{\\"name\\":\\"test\\"}", "indent": 2}',
    'base64-codec': '{"action": "encode", "text": "hello"}',
    'string-utils': '{"operation": "reverse", "text": "hello"}'
};

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function apiFetch(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
        showToast('登录已过期，请重新登录', 'error');
        logout();
        throw new Error('Unauthorized');
    }
    if (!response.ok) {
        let detail = '请求失败';
        try {
            const data = await response.json();
            detail = data.detail || detail;
        } catch (e) {}
        throw new Error(detail);
    }
    return response.json();
}

function switchView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-view="${viewId}"]`).classList.add('active');
}

function showRegister() {
    document.getElementById('register-section').style.display = 'block';
}

async function login() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    if (!username || !password) {
        showToast('请输入用户名和密码', 'error');
        return;
    }
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '登录中...';
    try {
        const response = await fetch('/token', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });
        if (response.ok) {
            const data = await response.json();
            token = data.access_token;
            localStorage.setItem('sases_token', token);
            showToast('登录成功', 'success');
            showMain();
        } else {
            const error = await response.json();
            showToast(error.detail || '登录失败', 'error');
        }
    } catch (e) {
        showToast('网络错误：' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '登录';
    }
}

async function register() {
    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    if (!username || !email || !password) {
        showToast('请填写完整注册信息', 'error');
        return;
    }
    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, email, password})
        });
        if (response.ok) {
            showToast('注册成功，请登录', 'success');
            document.getElementById('register-section').style.display = 'none';
        } else {
            const error = await response.json();
            showToast(error.detail || '注册失败', 'error');
        }
    } catch (e) {
        showToast('网络错误：' + e.message, 'error');
    }
}

function logout() {
    localStorage.removeItem('sases_token');
    token = null;
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('main-section').style.display = 'none';
    const loginBtn = document.querySelector('#auth-section button[onclick="login()"]');
    if (loginBtn) {
        loginBtn.disabled = false;
        loginBtn.textContent = '登录';
    }
}

async function showMain() {
    document.getElementById('auth-section').style.display = 'none';
    document.getElementById('main-section').style.display = 'block';
    switchView('view-chat');
    try {
        const data = await apiFetch('/me');
        document.getElementById('username-display').textContent = data.username;
        document.getElementById('credits-display').textContent = data.credits;
    } catch (e) {}
    loadSettings();
    loadLeaderboard();
    loadAssistantUnread();
    loadStats();
}

function handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
        showToast('图片大小不能超过 5MB', 'error');
        return;
    }
    const reader = new FileReader();
    reader.onload = function(e) {
        selectedImageBase64 = e.target.result.split(',')[1];
        document.getElementById('image-preview').innerHTML = `
            <div style="display:flex; align-items:center;">
                <img src="data:image/jpeg;base64,${selectedImageBase64}" style="max-width:80px; max-height:80px; margin-right:5px;" />
                <button onclick="clearSelectedFile('image')" style="margin-left:5px;">移除</button>
            </div>`;
        document.getElementById('chat-image').value = '';
    };
    reader.readAsDataURL(file);
}

function handleAudioSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
        showToast('音频大小不能超过 10MB', 'error');
        return;
    }
    const reader = new FileReader();
    reader.onload = function(e) {
        selectedAudioBase64 = e.target.result.split(',')[1];
        showToast('已选择音频：' + file.name, 'info');
        document.getElementById('chat-audio').value = '';
    };
    reader.readAsDataURL(file);
}

function handleVideoSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 25 * 1024 * 1024) {
        showToast('视频大小不能超过 25MB', 'error');
        return;
    }
    const reader = new FileReader();
    reader.onload = function(e) {
        selectedVideoBase64 = e.target.result.split(',')[1];
        showToast('已选择视频：' + file.name, 'info');
        document.getElementById('chat-video').value = '';
    };
    reader.readAsDataURL(file);
}

function clearSelectedFile(type) {
    if (type === 'image') {
        selectedImageBase64 = null;
        document.getElementById('image-preview').innerHTML = '';
    } else if (type === 'audio') {
        selectedAudioBase64 = null;
    } else if (type === 'video') {
        selectedVideoBase64 = null;
    }
}

async function chat() {
    const query = document.getElementById('chat-input').value.trim();
    const image = selectedImageBase64;
    const audio = selectedAudioBase64;
    const video = selectedVideoBase64;

    if (!query && !image && !audio && !video) {
        showToast('请输入问题或选择文件', 'error');
        return;
    }

    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;
    sendBtn.textContent = '发送中...';
    document.getElementById('chat-loading').style.display = 'flex';
    document.getElementById('chat-error').style.display = 'none';

    const payload = { query };
    if (image) payload.image = image;
    if (audio) payload.audio = audio;
    if (video) payload.video = video;

    try {
        const data = await apiFetch('/chat', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        document.getElementById('chat-result').textContent = data.answer;
        clearSelectedFile('image');
        clearSelectedFile('audio');
        clearSelectedFile('video');
        if (data.deducted) {
            showToast(`本次查询已扣除 ${data.deducted} 积分`, 'info');
            updateCreditsDisplay();
        }
    } catch (e) {
        document.getElementById('chat-error').textContent = e.message;
        document.getElementById('chat-error').style.display = 'block';
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = '发送';
        document.getElementById('chat-loading').style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const input = document.getElementById('chat-input');
    if (input) {
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chat();
            }
        });
    }
});

async function showLedger() {
    try {
        const data = await apiFetch('/my_ledger');
        const div = document.getElementById('ledger');
        div.style.display = 'block';
        div.innerHTML = '<h3>积分流水</h3>';
        const ul = document.createElement('ul');
        data.ledger.forEach(item => {
            const li = document.createElement('li');
            li.textContent = `${item.amount > 0 ? '+' : ''}${item.amount} 积分 - ${item.reason} (${item.timestamp})`;
            ul.appendChild(li);
        });
        div.appendChild(ul);
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function submitSeed() {
    if (!localStorage.getItem('seed_risk_dismissed')) {
        const dismiss = confirm('提示：提交的种子将进入 SASES 公共种子池，并被其他用户或系统使用。请勿包含个人隐私信息。\n\n点击“确定”继续，并永久不再提示；点击“取消”返回。');
        if (!dismiss) return;
        localStorage.setItem('seed_risk_dismissed', 'true');
    }
    const description = document.getElementById('seed-desc').value.trim();
    const testcases_str = document.getElementById('seed-testcases').value.trim();
    let test_cases = [];
    try { test_cases = testcases_str ? JSON.parse(testcases_str) : []; } catch(e) {
        showToast('测试用例 JSON 格式错误', 'error');
        return;
    }
    try {
        await apiFetch('/submit_seed', {
            method: 'POST',
            body: JSON.stringify({description, test_cases})
        });
        showToast('种子已提交', 'success');
        document.getElementById('seed-desc').value = '';
        document.getElementById('seed-testcases').value = '';
        loadAssistantUnread();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function updateCreditsDisplay() {
    try {
        const data = await apiFetch('/me');
        document.getElementById('credits-display').textContent = data.credits;
    } catch (e) {}
}

async function loadLeaderboard() {
    try {
        const data = await apiFetch('/leaderboard');
        const list = document.getElementById('leaderboard');
        list.innerHTML = '';
        data.forEach(item => {
            const li = document.createElement('li');
            li.textContent = `${item.username}: ${item.credits} 积分`;
            list.appendChild(li);
        });
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function loadContribLeaderboard() {
    try {
        const data = await apiFetch('/contrib_leaderboard');
        const div = document.getElementById('discover-content');
        div.innerHTML = '<h3>贡献榜</h3>';
        const ul = document.createElement('ul');
        data.forEach(item => {
            const li = document.createElement('li');
            li.textContent = `${item.username}: ${item.score}`;
            ul.appendChild(li);
        });
        div.appendChild(ul);
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function loadStats() {
    try {
        const data = await apiFetch('/stats');
        document.getElementById('stats').textContent = JSON.stringify(data, null, 2);
    } catch (e) {}
}

function toggleStats() {
    const stats = document.getElementById('stats');
    stats.style.display = stats.style.display === 'none' ? 'block' : 'none';
}

async function loadSettings() {
    try {
        const data = await apiFetch('/me/settings');
        document.getElementById('auto-pollinate-toggle').checked = data.auto_pollinate_enabled;
    } catch (e) {}
}

async function toggleAutoPollinate() {
    const enabled = document.getElementById('auto-pollinate-toggle').checked;
    try {
        await apiFetch('/me/settings', {
            method: 'PATCH',
            body: JSON.stringify({auto_pollinate_enabled: enabled})
        });
        showToast('设置已更新', 'success');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function loadAssistantUnread() {
    try {
        const data = await apiFetch('/assistant/messages');
        const badge = document.getElementById('assistant-unread');
        if (data.unread > 0) {
            badge.textContent = data.unread;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    } catch (e) {}
}

async function showAssistant() {
    try {
        const data = await apiFetch('/assistant/messages');
        const div = document.getElementById('assistant-messages');
        div.style.display = 'block';
        div.innerHTML = '<h3>SASES助手</h3>';
        const ul = document.createElement('ul');
        data.messages.forEach(msg => {
            const li = document.createElement('li');
            li.textContent = `${msg.title}：${msg.content} (${msg.timestamp})`;
            ul.appendChild(li);
        });
        div.appendChild(ul);
        await apiFetch('/assistant/read', { method: 'POST' });
        loadAssistantUnread();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

let toolList = [];

async function loadToolList() {
    try {
        const data = await apiFetch('/harness/tools');
        toolList = data;
        const select = document.getElementById('tool-select');
        select.innerHTML = '';
        toolList.forEach(tool => {
            const opt = document.createElement('option');
            opt.value = tool.module_id;
            opt.textContent = `${tool.name} (${tool.module_id})`;
            select.appendChild(opt);
        });
        select.onchange = updateToolExample;
        updateToolExample();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function updateToolExample() {
    const moduleId = document.getElementById('tool-select').value;
    const example = TOOL_EXAMPLES[moduleId] || '';
    document.getElementById('tool-params-example').textContent = example ? `示例: ${example}` : '';
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
        try { params = JSON.parse(paramsText); } catch(e) {
            showToast('参数 JSON 格式错误', 'error');
            return;
        }
    }
    try {
        const data = await apiFetch('/harness/invoke', {
            method: 'POST',
            body: JSON.stringify({ module_id: moduleId, params })
        });
        document.getElementById('tool-result').textContent = JSON.stringify(data, null, 2);
    } catch (e) {
        showToast(e.message, 'error');
    }
}

let nodeList = [];

async function loadNodeList() {
    try {
        const data = await apiFetch('/space/nodes');
        nodeList = data;
        const ul = document.getElementById('node-list');
        ul.innerHTML = '';
        nodeList.forEach(node => {
            const li = document.createElement('li');
            li.style.display = 'flex';
            li.style.justifyContent = 'space-between';
            li.style.alignItems = 'center';

            const statusText = node.status || 'unknown';
            const statusColor = statusText === 'online' ? 'green' : statusText === 'offline' ? 'red' : 'gray';
            const statusSpan = document.createElement('span');
            statusSpan.style.color = statusColor;
            statusSpan.style.marginRight = '5px';
            statusSpan.textContent = '●';
            li.appendChild(statusSpan);
            const textSpan = document.createElement('span');
            textSpan.textContent = `${statusText} ${node.name} (${node.node_id})`;
            li.appendChild(textSpan);

            const btn = document.createElement('button');
            btn.textContent = '调用';
            btn.onclick = () => invokeNode(node.node_id);
            li.appendChild(btn);
            ul.appendChild(li);
        });
    } catch (e) {
        showToast(e.message, 'error');
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
    const paramsText = prompt(`输入调用节点 ${nodeId} 的参数 JSON（留空表示 {}）：`);
    let params = {};
    if (paramsText && paramsText.trim() !== '') {
        try {
            params = JSON.parse(paramsText);
            if (typeof params !== 'object' || Array.isArray(params)) {
                showToast('参数必须是 JSON 对象', 'error');
                return;
            }
        } catch (e) {
            showToast('参数 JSON 格式错误', 'error');
            return;
        }
    }
    try {
        const data = await apiFetch('/space/invoke', {
            method: 'POST',
            body: JSON.stringify({ node_id: nodeId, params })
        });
        document.getElementById('node-invoke-result').textContent = JSON.stringify(data, null, 2);
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function exportKnowledgeBase() {
    try {
        const data = await apiFetch('/kb/export');
        const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'success_kb.json';
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function loadGeneralSettings() {
    try {
        const data = await apiFetch('/me/settings/all');
        document.getElementById('general-settings-json').value = JSON.stringify(data, null, 2);
    } catch (e) {
        showToast(e.message, 'error');
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
    try { settings = JSON.parse(text); } catch(e) {
        showToast('设置 JSON 格式错误', 'error');
        return;
    }
    try {
        await apiFetch('/me/settings/all', {
            method: 'PATCH',
            body: JSON.stringify({settings})
        });
        showToast('设置已保存', 'success');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

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
    try {
        const data = await apiFetch('/api_keys');
        const ul = document.getElementById('api-key-list');
        ul.innerHTML = '';
        data.forEach(k => {
            const li = document.createElement('li');
            li.style.display = 'flex';
            li.style.justifyContent = 'space-between';
            li.style.alignItems = 'center';
            const span = document.createElement('span');
            span.textContent = `${k.provider} - ${k.masked_key} (优先级:${k.priority})`;
            li.appendChild(span);

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
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function addApiKey() {
    const provider = document.getElementById('api-key-provider').value;
    const key = document.getElementById('api-key-value').value.trim();
    const priority = parseInt(document.getElementById('api-key-priority').value) || 1;
    if (!provider || !key) {
        showToast('请填写提供商和 API Key', 'error');
        return;
    }
    try {
        await apiFetch('/api_keys', {
            method: 'POST',
            body: JSON.stringify({provider, key, priority})
        });
        showToast('API Key 已添加', 'success');
        document.getElementById('api-key-value').value = '';
        loadApiKeys();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function deleteApiKey(id) {
    if (!confirm('确认删除该 API Key？')) return;
    try {
        await apiFetch(`/api_keys/${id}`, { method: 'DELETE' });
        showToast('已删除', 'success');
        loadApiKeys();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function setApiKeyPriority(id) {
    const priority = prompt('输入新的优先级（数字越小越优先，1为最高）：');
    if (!priority) return;
    try {
        await apiFetch('/api_keys/priority', {
            method: 'PATCH',
            body: JSON.stringify({key_id: id, priority: parseInt(priority)})
        });
        showToast('优先级已更新', 'success');
        loadApiKeys();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

if (token) {
    showMain();
}