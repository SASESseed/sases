// 公共工具与全局状态
export let token = localStorage.getItem('sases_token');

export function setToken(newToken) {
    token = newToken;
    if (newToken) {
        localStorage.setItem('sases_token', newToken);
    } else {
        localStorage.removeItem('sases_token');
    }
}

export function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

export function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

export async function apiFetch(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
        showToast('登录已过期，请重新登录', 'error');
        // 触发登出
        if (typeof window !== 'undefined' && window.logout) {
            window.logout();
        }
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

export function switchView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const navItem = document.querySelector(`.nav-item[data-view="${viewId}"]`);
    if (navItem) navItem.classList.add('active');
}