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
}

async function submitSeed() {
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
    } else {
        alert('提交失败');
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

// 如果已有 token，自动进入主界面
if (token) {
    showMain();
}