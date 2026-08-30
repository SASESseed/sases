import { token, showToast, apiFetch, switchView } from './utils.js';
import { initAuth, logout } from './auth.js';
import { initChat } from './chat.js';
import { initContacts, loadAssistantUnread } from './contacts.js';
import { initDiscover } from './discover.js';
import { initMe, initMeData } from './me.js';

// 将 logout 挂到全局供 utils 中使用
window.logout = logout;

async function loadUserInfo() {
    try {
        const data = await apiFetch('/me');
        document.getElementById('username-display').textContent = data.username;
        document.getElementById('credits-display').textContent = data.credits;
    } catch (e) {}
}

async function initApp() {
    // 初始隐藏所有视图，显示聊天
    switchView('view-chat');

    // 初始化各模块
    initAuth();
    initChat();
    initContacts();
    initDiscover();
    initMe();

    // 绑定底部导航
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const viewId = item.dataset.view;
            switchView(viewId);
        });
    });

    // 如果已有 token，加载主界面
    if (token) {
        document.getElementById('auth-section').style.display = 'none';
        document.getElementById('main-section').style.display = 'block';
        await loadUserInfo();
        await initMeData();
        loadAssistantUnread();
        // 触发其他数据加载
        document.dispatchEvent(new CustomEvent('sases-main-loaded'));
    } else {
        document.getElementById('auth-section').style.display = 'block';
        document.getElementById('main-section').style.display = 'none';
    }
}

// 登录成功事件
document.addEventListener('sases-login-success', async () => {
    document.getElementById('auth-section').style.display = 'none';
    document.getElementById('main-section').style.display = 'block';
    await loadUserInfo();
    await initMeData();
    loadAssistantUnread();
    document.dispatchEvent(new CustomEvent('sases-main-loaded'));
});

// 积分更新事件
document.addEventListener('sases-credits-updated', loadUserInfo);

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initApp);