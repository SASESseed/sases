import { setToken, showToast, apiFetch } from './utils.js';

export function initAuth() {
    // 登录
    const loginBtn = document.querySelector('#auth-section button[onclick="login()"]');
    if (loginBtn) {
        loginBtn.addEventListener('click', login);
    }
    // 注册
    const registerBtn = document.querySelector('#auth-section button[onclick="register()"]');
    if (registerBtn) {
        registerBtn.addEventListener('click', register);
    }
    // 注册入口显示
    const showRegisterBtn = document.querySelector('#auth-section button[onclick="showRegister()"]');
    if (showRegisterBtn) {
        showRegisterBtn.addEventListener('click', showRegister);
    }
    // 登出按钮（可能在其他模块中，但统一绑定）
    const logoutBtns = document.querySelectorAll('[data-action="logout"]');
    logoutBtns.forEach(btn => btn.addEventListener('click', logout));
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
            setToken(data.access_token);
            showToast('登录成功', 'success');
            // 触发主界面加载
            document.dispatchEvent(new CustomEvent('sases-login-success'));
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

export function logout() {
    setToken(null);
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('main-section').style.display = 'none';
    const loginBtn = document.querySelector('#auth-section button[onclick="login()"]');
    if (loginBtn) {
        loginBtn.disabled = false;
        loginBtn.textContent = '登录';
    }
}