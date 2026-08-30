let token = localStorage.getItem('sases_token');
let currentPage = 'page-chat';

// ========== 认证相关 ==========
function showRegister() {
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('register-form').style.display = 'block';
}
function showLogin() {
    document.getElementById('login-form').style.display = 'block';
    document.getElementById('register-form').style.display = 'none';
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
        showLogin();
    } else {
        alert('注册失败');
    }
}
function logout() {
    localStorage.removeItem('sases_token');
    token = null;
    const auth = document.getElementById('auth-section');
    const main = document.getElementById('main-app');
    if (auth) auth.style.display = 'flex';
    if (main) main.style.display = 'none';
}

// ========== 页面切换 ==========
function switchPage(pageId) {
    currentPage = pageId;
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const page = document.getElementById(pageId);
    if (page) page.classList.add('active');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const nav = document.querySelector(`.nav-item[data-page="${pageId}"]`);
    if (nav) nav.classList.add('active');
    const titles = {
        'page-chat': '聊天',
        'page-nodes': '节点',
        'page-discover': '发现',
        'page-profile': '我的'
    };
    const titleEl = document.getElementById('page-title');
    if (titleEl) titleEl.textContent = titles[pageId] || 'SASES';
    if (pageId === 'page-nodes') {
        loadSpaceNodes();
        loadHarnessTools();
    } else if (pageId === 'page-discover') {
        loadLeaderboard();
        loadContribLeaderboard();
        loadStats();
    } else if (pageId === 'page-profile') {
        loadProfile();
    }
}

// ========== 主界面显示 ==========
async function showMain() {
    const auth = document.getElementById('auth-section');
    const main = document.getElementById('main-app');
    // 防御性检查，避免元素缺失导致整个脚本崩溃
    if (!auth || !main) {
        console.error('缺失必要的页面元素：auth-section 或 main-app');
        alert('页面结构错误，请检查 index.html');
        return;
    }
    auth.style.display = 'none';
    main.style.display = 'flex';
    await loadProfile();
    switchPage('page-chat');
}

// ========== 个人信息 ==========
async function loadProfile() {
    const res = await fetch('/me', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        const uname = document.getElementById('username-display');
        const credits = document.getElementById('credits-display');
        const credits2 = document.getElementById('credits-display-2');
        if (uname) uname.textContent = data.username;
        if (credits) credits.textContent = data.credits;
        if (credits2) credits2.textContent = data.credits;
    }
}

// ========== 聊天 ==========
async function sendChat() {
    const input = document.getElementById('chat-input');
    if (!input) return;
    const query = input.value.trim();
    if (!query) return;
    const messagesDiv = document.getElementById('chat-messages');
    if (messagesDiv) {
        messagesDiv.innerHTML += `<div style="text-align:right; margin:5px 0;"><span style="background:#95ec69; padding:8px; border-radius:8px; display:inline-block;">${query}</span></div>`;
    }
    input.value = '';
    const res = await fetch('/chat', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({query})
    });
    if (res.ok) {
        const data = await res.json();
        if (messagesDiv) {
            messagesDiv.innerHTML += `<div style="text-align:left; margin:5px 0;"><span style="background:white; padding:8px; border-radius:8px; display:inline-block;">${data.answer}</span></div>`;
        }
        if (data.deducted) {
            alert(`本次查询扣除 ${data.deducted} 积分`);
            loadProfile();
        }
    } else if (res.status === 402) {
        alert('积分不足，无法查询');
    } else {
        alert('请求失败');
    }
    if (messagesDiv) messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// ========== 种子提交 ==========
async function submitSeed() {
    const desc = document.getElementById('seed-desc');
    const tc = document.getElementById('seed-testcases');
    if (!desc || !tc) return;
    const description = desc.value;
    const testcases_str = tc.value;
    let test_cases = [];
    try {
        test_cases = JSON.parse(testcases_str) || [];
    } catch(e) {
        alert('测试用例 JSON 格式错误');
        return;
    }
    const res = await fetch('/submit_seed', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({description, test_cases})
    });
    if (res.ok) alert('种子已提交');
    else alert('提交失败');
}

// ========== AGI 执行 ==========
async function executeAGI() {
    const query = document.getElementById('agi-query').value.trim();
    if (!query) return;
    const res = await fetch('/agi/execute', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({query})
    });
    const data = await res.json();
    const resultDiv = document.getElementById('agi-result');
    if (resultDiv) resultDiv.textContent = JSON.stringify(data, null, 2);
}

// ========== 排行榜 ==========
async function loadLeaderboard() {
    const res = await fetch('/leaderboard');
    const data = await res.json();
    const list = document.getElementById('leaderboard-list');
    if (!list) return;
    list.innerHTML = '<h3>积分榜</h3>';
    data.forEach(item => {
        const li = document.createElement('li');
        li.textContent = `${item.username}: ${item.credits} 积分`;
        list.appendChild(li);
    });
}
async function loadContribLeaderboard() {
    const res = await fetch('/contrib_leaderboard');
    const data = await res.json();
    const list = document.getElementById('leaderboard-list');
    if (!list) return;
    list.innerHTML += '<h3>贡献榜</h3>';
    data.forEach(item => {
        const li = document.createElement('li');
        li.textContent = `${item.username}: ${item.score} 分`;
        list.appendChild(li);
    });
}

// ========== 统计 ==========
async function loadStats() {
    const res = await fetch('/stats');
    const data = await res.json();
    const el = document.getElementById('stats-display');
    if (el) el.textContent = JSON.stringify(data, null, 2);
}

// ========== 积分流水 ==========
async function showLedger() {
    const res = await fetch('/my_ledger', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        const div = document.getElementById('ledger');
        if (div) {
            div.style.display = 'block';
            div.innerHTML = '<h3>积分流水</h3><ul>' + data.ledger.map(item =>
                `<li>${item.amount > 0 ? '+' : ''}${item.amount} 积分 - ${item.reason} (${item.timestamp})</li>`
            ).join('') + '</ul>';
        }
    }
}

// ========== SASES 助手消息 ==========
async function showAssistant() {
    const res = await fetch('/assistant/messages', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        const div = document.getElementById('assistant-messages');
        if (div) {
            div.style.display = 'block';
            div.innerHTML = '<h3>SASES助手</h3><ul>' + data.messages.map(msg =>
                `<li><strong>${msg.title}</strong>：${msg.content} <small>(${msg.timestamp})</small></li>`
            ).join('') + '</ul>';
        }
        await fetch('/assistant/read', {
            method: 'POST',
            headers: {'Authorization': `Bearer ${token}`}
        });
    }
}

// ========== 授粉设置 ==========
async function loadSettings() {
    const res = await fetch('/me/settings', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        const toggle = document.getElementById('auto-pollinate-toggle');
        if (toggle) toggle.checked = data.auto_pollinate_enabled;
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
    if (res.ok) alert('设置已更新');
    else alert('更新失败');
}

// ========== 空间节点 ==========
async function loadSpaceNodes() {
    const res = await fetch('/space/nodes');
    const data = await res.json();
    const div = document.getElementById('space-nodes-list');
    if (!div) return;
    div.innerHTML = '';
    data.forEach(node => {
        const item = document.createElement('div');
        item.style.border = '1px solid #ddd';
        item.style.padding = '8px';
        item.style.margin = '5px 0';
        item.innerHTML = `<strong>${node.name}</strong> (${node.node_type})<br>${node.description}`;
        div.appendChild(item);
    });
}

// ========== Harness 工具 ==========
async function loadHarnessTools() {
    const res = await fetch('/harness/tools');
    const data = await res.json();
    const div = document.getElementById('harness-tools-list');
    if (!div) return;
    div.innerHTML = '';
    data.forEach(tool => {
        const item = document.createElement('div');
        item.style.border = '1px solid #ddd';
        item.style.padding = '8px';
        item.style.margin = '5px 0';
        item.innerHTML = `<strong>${tool.name}</strong> (${tool.module_id})<br>${tool.description}`;
        div.appendChild(item);
    });
}

// ========== 初始化 ==========
if (token) {
    showMain();
} else {
    const auth = document.getElementById('auth-section');
    if (auth) auth.style.display = 'flex';
}