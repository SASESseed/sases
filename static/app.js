let token = localStorage.getItem('sases_token');

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

    const res = await fetch('/me', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        document.getElementById('username-display').textContent = data.username;
        document.getElementById('credits-display').textContent = data.credits;
    }

    loadLeaderboard();
    loadStats();
    loadSettings();
    checkPendingPollinate();
    loadAssistantUnread();
}

function logout() {
    localStorage.removeItem('sases_token');
    token = null;
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('main-section').style.display = 'none';
}

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

async function submitSeed() {
    if (!localStorage.getItem('seed_risk_dismissed')) {
        const dismiss = confirm('提示：提交的种子将进入 SASES 公共种子池，并被其他用户或系统使用。请勿包含个人隐私信息。\n\n点击“确定”继续，并永久不再提示；点击“取消”返回。');
        if (!dismiss) return;
        localStorage.setItem('seed_risk_dismissed', 'true');
    }

    const description = document.getElementById('seed-desc').value;
    const testcases_str = document.getElementById('seed-testcases').value;
    let test_cases = [];
    try {
        test_cases = JSON.parse(testcases_str) || [];
    } catch(e) {
        test_cases = [];
    }
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

async function checkPendingPollinate() {
    const settingsRes = await fetch('/me/settings', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    let autoPollinate = true;
    if (settingsRes.ok) {
        const settings = await settingsRes.json();
        autoPollinate = settings.auto_pollinate_enabled;
    }

    if (autoPollinate) return;

    if (localStorage.getItem('pollinate_auto_confirm') === 'true') return;

    const res = await fetch('/pollinate/pending', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        if (data.has_pending) {
            document.getElementById('pollinate-pending').style.display = 'block';
            window._pendingPollinate = data;
        }
    }
}

async function confirmPollinate() {
    const res = await fetch('/pollinate/confirm', {
        method: 'POST',
        headers: {'Authorization': `Bearer ${token}`}
    });
    const resultDiv = document.getElementById('pollinate-result');
    if (res.ok) {
        const data = await res.json();
        resultDiv.textContent = data.message || '授粉成功';
        document.getElementById('pollinate-pending').style.display = 'none';
        localStorage.setItem('pollinate_auto_confirm', 'true');
        updateCreditsDisplay();
        loadAssistantUnread();
    } else {
        const err = await res.json();
        resultDiv.textContent = `失败：${err.detail || res.status}`;
    }
}

async function dismissPollinate() {
    document.getElementById('pollinate-pending').style.display = 'none';
}

async function updateCreditsDisplay() {
    const res = await fetch('/me', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        document.getElementById('credits-display').textContent = data.credits;
    }
}

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

async function loadStats() {
    const res = await fetch('/stats');
    const data = await res.json();
    document.getElementById('stats').textContent = JSON.stringify(data, null, 2);
}

async function loadSettings() {
    const res = await fetch('/me/settings', {
        headers: {'Authorization': `Bearer ${token}`}
    });
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
    if (res.ok) {
        alert('设置已更新');
        checkPendingPollinate();
    } else {
        alert('设置更新失败');
    }
}

// ========== SASES 助手 ==========
async function loadAssistantUnread() {
    const res = await fetch('/assistant/messages', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        const badge = document.getElementById('assistant-unread');
        if (data.unread > 0) {
            badge.textContent = `（${data.unread}条未读）`;
        } else {
            badge.textContent = '';
        }
    }
}

async function showAssistant() {
    const res = await fetch('/assistant/messages', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    if (res.ok) {
        const data = await res.json();
        const div = document.getElementById('assistant-messages');
        div.style.display = 'block';
        div.innerHTML = '<h3>SASES助手</h3><ul>' + data.messages.map(msg => 
            `<li><strong>${msg.title}</strong>：${msg.content} <small>(${msg.timestamp})</small></li>`
        ).join('') + '</ul>';

        // 标记已读
        await fetch('/assistant/read', {
            method: 'POST',
            headers: {'Authorization': `Bearer ${token}`}
        });
        loadAssistantUnread();
    } else {
        alert('获取助手消息失败');
    }
}

// 如果已有 token，自动进入主界面
if (token) {
    showMain();
}