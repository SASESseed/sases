import { apiFetch, showToast } from './utils.js';

export function initContacts() {
    // 绑定 SASES 助手点击
    const assistantItem = document.querySelector('.setting-item[data-action="assistant"]');
    if (assistantItem) assistantItem.addEventListener('click', showAssistant);
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

export async function loadAssistantUnread() {
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