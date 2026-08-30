import { apiFetch, showToast } from './utils.js';

const TOOL_EXAMPLES = {
    'unit-converter': '{"celsius": 30}',
    'calculator': '{"expression": "2+3*4"}',
    'text-stats': '{"text": "Hello world. Hello again."}',
    'json-formatter': '{"json_string": "{\\"name\\":\\"test\\"}", "indent": 2}',
    'base64-codec': '{"action": "encode", "text": "hello"}',
    'string-utils': '{"operation": "reverse", "text": "hello"}'
};

export function initDiscover() {
    // 排行榜
    document.querySelector('[data-action="leaderboard"]').addEventListener('click', loadLeaderboard);
    document.querySelector('[data-action="contrib"]').addEventListener('click', loadContribLeaderboard);
    document.querySelector('[data-action="harness-panel"]').addEventListener('click', toggleHarnessPanel);
    document.querySelector('[data-action="node-panel"]').addEventListener('click', toggleNodePanel);
    // 工具执行按钮
    document.getElementById('invoke-tool-btn').addEventListener('click', invokeTool);
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

async function loadToolList() {
    try {
        const data = await apiFetch('/harness/tools');
        const select = document.getElementById('tool-select');
        select.innerHTML = '';
        data.forEach(tool => {
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

async function loadNodeList() {
    try {
        const data = await apiFetch('/space/nodes');
        const ul = document.getElementById('node-list');
        ul.innerHTML = '';
        data.forEach(node => {
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
            btn.addEventListener('click', () => invokeNode(node.node_id));
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