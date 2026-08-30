import { apiFetch, showToast } from './utils.js';

export function initMe() {
    // 自动授粉开关
    document.getElementById('auto-pollinate-toggle').addEventListener('change', toggleAutoPollinate);
    // 积分流水
    document.querySelector('[data-action="ledger"]').addEventListener('click', showLedger);
    // 统计
    document.querySelector('[data-action="stats"]').addEventListener('click', toggleStats);
    // 导出知识库
    document.querySelector('[data-action="export-kb"]').addEventListener('click', exportKnowledgeBase);
    // 通用设置
    document.querySelector('[data-action="general-settings"]').addEventListener('click', toggleGeneralSettings);
    document.getElementById('save-general-settings').addEventListener('click', saveGeneralSettings);
    // API Key 管理
    document.querySelector('[data-action="api-keys"]').addEventListener('click', toggleApiKeyPanel);
    document.getElementById('add-api-key-btn').addEventListener('click', addApiKey);
    // 提交种子
    document.getElementById('submit-seed-btn').addEventListener('click', submitSeed);
}

async function loadSettings() {
    try {
        const data = await apiFetch('/me/settings');
        document.getElementById('auto-pollinate-toggle').checked = data.auto_pollinate_enabled;
    } catch (e) {}
}

export async function initMeData() {
    await loadSettings();
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
            btnPriority.addEventListener('click', () => setApiKeyPriority(k.id));
            const btnDel = document.createElement('button');
            btnDel.textContent = '删除';
            btnDel.addEventListener('click', () => deleteApiKey(k.id));
            li.appendChild(btnPriority);
            li.appendChild(btnDel);
            ul.appendChild(li);
        });
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function toggleApiKeyPanel() {
    const panel = document.getElementById('api-key-panel');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        loadApiKeys();
    } else {
        panel.style.display = 'none';
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
    } catch (e) {
        showToast(e.message, 'error');
    }
}