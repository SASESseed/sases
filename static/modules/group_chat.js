// static/modules/group_chat.js
import { api } from './api.js';

let currentGroupId = null;
let currentGroupName = '';
let currentAgentId = null; // 当前使用的智能体身份，null 表示用户本人
let currentGroupMode = 'normal'; // normal 或 swarm
let currentUserId = null; // 当前登录用户ID
window._gcDebug = { getUserId: () => currentUserId, getAgentId: () => currentAgentId, getGroupId: () => currentGroupId };

export async function openGroupChat(groupId, groupName) {
  currentGroupId = groupId;

  window.currentGroupId = groupId;
  currentGroupName = groupName;
  currentAgentId = null;
  currentGroupMode = 'normal';
  window.currentGroupChat = true;

  // 获取当前用户ID（await 保证 loadGroupMessages 前就绪）
  try {
    const _me = await api.getMe();
    currentUserId = _me.user_id;
  } catch (_e) {
    currentUserId = null;
  }

  document.getElementById('chat-window-title').textContent = groupName;
  document.getElementById('view-chat-window').style.display = 'flex';
  document.querySelector('.bottom-nav').style.display = 'none';
  document.querySelector('.top-bar').style.display = 'none';

  const settingsBtn = document.getElementById('group-settings-btn');
  if (settingsBtn) {
    settingsBtn.style.display = 'block';
    settingsBtn.onclick = openGroupSettings;
  }

  const identityBtn = document.getElementById('identity-btn');
  if (identityBtn) identityBtn.style.display = 'block';

  const modeBtn = document.getElementById('chat-mode-btn');
  if (modeBtn) {
    modeBtn.style.display = 'block';
    modeBtn.onclick = openGroupModeMenu;
  }
  const modeText = document.getElementById('chat-mode-text');
  if (modeText) modeText.textContent = '普通聊天';

  const _plusBtn = document.getElementById('input-plus-btn');
  if (_plusBtn) {
    _plusBtn.onclick = () => {
      import('./chat_menu.js').then(m => m.toggleChatPlusPanel());
    };
  }
  const _chatInput = document.getElementById('chat-input');
  if (_chatInput) {
    _chatInput.oninput = () => {
      if (window.updateSendButtonVisibility) window.updateSendButtonVisibility();
    };
  }
  const _sendBtn = document.getElementById('send-btn');
  if (_sendBtn) _sendBtn.onclick = sendGroupMessage;

  loadGroupTasks();


  const messagesContainer = document.getElementById('chat-messages');
  // 建立 WebSocket 连接
  try {
    if (window._groupWs) {
      window._groupWs.close();
      window._groupWs = null;
    }
    api.getGroupInfo(groupId).then(info => {
      const ggid = info && info.global_group_id;
      if (!ggid) return;
      const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/group/' + encodeURIComponent(ggid);
      const ws = new WebSocket(wsUrl);
      ws.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data);
          if (d && d.type === 'message') {
            loadGroupMessages();
          }
        } catch (err) {}
      };
      ws.onopen = () => console.log('[ws] connected to', ggid);
      ws.onclose = () => console.log('[ws] disconnected');
      window._groupWs = ws;
    }).catch(() => {});
  } catch (e) {
    console.warn('[ws] setup failed:', e);
  }
  messagesContainer.innerHTML = '';
  loadGroupMessages();
}

export function closeGroupChat() {
  currentGroupId = null;

  window.currentGroupId = null;
  currentGroupName = '';
  currentAgentId = null;
  currentGroupMode = 'normal';
  currentUserId = null;
  window.currentGroupChat = false;

  document.getElementById('view-chat-window').style.display = 'none';
  document.querySelector('.bottom-nav').style.display = 'flex';
  document.querySelector('.top-bar').style.display = 'flex';

  const settingsBtn = document.getElementById('group-settings-btn');
  if (settingsBtn) settingsBtn.style.display = 'none';
  const identityBtn = document.getElementById('identity-btn');
  if (identityBtn) identityBtn.style.display = 'none';
  const modeBtn = document.getElementById('chat-mode-btn');
  if (modeBtn) modeBtn.style.display = 'none';
}

async function loadGroupTasks() {
  if (!currentGroupId) return;
  try {
    const data = await api.getGroupTasks(currentGroupId, 'open');
    const tasks = data.tasks || [];
    const bar = document.getElementById('group-task-bar');
    const text = document.getElementById('group-task-bar-text');
    if (!bar || !text) return;
    if (tasks.length === 0) {
      bar.style.display = 'none';
      return;
    }
    text.textContent = '进行中任务 (' + tasks.length + ')';
    bar.style.display = 'flex';
    bar.onclick = function() {
      openTaskListPage(tasks);
    };
  } catch (e) {
    console.log('loadGroupTasks error:', e);
  }
}

function openTaskListPage(tasks) {
  let html = '<div style="padding:12px;">';
  tasks.forEach(t => {
    html += '<div class="task-list-item" data-tid="' + t.id + '" style="border:1px solid #eee;border-radius:8px;padding:12px;margin-bottom:10px;cursor:pointer;">';
    html += '<div style="font-size:15px;font-weight:600;margin-bottom:4px;">' + (t.title || '未命名') + '</div>';
    html += '<div style="font-size:12px;color:#666;">质押 ' + (t.reward_credits || 0) + ' 积分 · ' + (t.task_category || 'text') + '</div>';
    html += '</div>';
  });
  html += '</div>';
  window.openSubpage('进行中任务', html);
  setTimeout(function() {
    document.querySelectorAll('.task-list-item').forEach(el => {
      el.onclick = function() {
        if (typeof window.openTaskDetail === 'function') window.openTaskDetail(parseInt(el.dataset.tid));
      };
    });
  }, 300);
}


window.openGroupRedPacket = async function(packetId) {
  try {
    const detail = await fetch('/group/red-packets/' + packetId, {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    }).then(r => r.json());
    if (detail.error || detail.detail) { alert('加载失败：' + (detail.error || detail.detail)); return; }
    let claimsHtml = '';
    if (detail.claims && detail.claims.length > 0) {
      claimsHtml = '<div style="margin-top:20px;"><div style="font-size:13px;color:#999;margin-bottom:8px;">领取记录</div>';
      detail.claims.forEach(c => {
        claimsHtml += '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f5f5f5;font-size:13px;"><span>' + (c.username || '匿名') + '</span><span style="color:#f59e0b;font-weight:600;">' + c.amount + ' 积分</span></div>';
      });
      claimsHtml += '</div>';
    }
    let bodyHtml = '';
    if (detail.claimed_by_me !== null && detail.claimed_by_me !== undefined) {
      bodyHtml = '<div style="font-size:48px;font-weight:700;color:#f59e0b;margin:20px 0;">' + detail.claimed_by_me + '</div><div style="font-size:14px;color:#666;">已存入你的积分</div>';
    } else if (detail.status === 'empty') {
      bodyHtml = '<div style="font-size:36px;color:#999;margin:20px 0;">已抢完</div>';
    } else if (detail.status === 'expired') {
      bodyHtml = '<div style="font-size:36px;color:#999;margin:20px 0;">已过期</div>';
    } else {
      bodyHtml = '<button id="grp-rp-claim-btn" style="width:180px;height:180px;border-radius:50%;background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#fff;font-size:24px;font-weight:700;border:none;cursor:pointer;margin:20px auto;display:block;box-shadow:0 8px 24px rgba(245,158,11,0.3);">開</button>';
    }
    const html = '<div style="text-align:center;padding:30px 20px;">'
      + '<div style="font-size:18px;font-weight:600;margin-bottom:8px;">' + (detail.message || '恭喜发财') + '</div>'
      + '<div style="font-size:13px;color:#999;margin-bottom:20px;">来自 ' + (detail.sender_name || '群友') + ' 的群红包</div>'
      + '<div style="background:linear-gradient(135deg,#fef3c7,#fed7aa);border-radius:16px;padding:30px 20px;margin:0 auto;">'
      + bodyHtml
      + '<div style="font-size:12px;color:#92400e;margin-top:12px;">' + detail.claimed_count + '/' + detail.total_count + ' 已领取 · 总额 ' + detail.total_amount + ' 积分</div>'
      + '</div>'
      + claimsHtml
      + '</div>';
    window.openSubpage('群红包', html);
    setTimeout(() => {
      const btn = document.getElementById('grp-rp-claim-btn');
      if (btn) {
        btn.onclick = async function() {
          btn.disabled = true;
          btn.textContent = '...';
          try {
            const resp = await fetch('/group/red-packets/' + packetId + '/claim', {
              method: 'POST',
              headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
            });
            const data = await resp.json();
            if (data.error || data.detail) { alert('领取失败：' + (data.error || data.detail)); btn.disabled = false; btn.textContent = '開'; return; }
            window.openGroupRedPacket(packetId);
            if (typeof loadGroupMessages === 'function') loadGroupMessages();
          } catch (e) { alert('网络错误：' + e.message); btn.disabled = false; btn.textContent = '開'; }
        };
      }
    }, 100);
  } catch (e) { alert('网络错误：' + e.message); }
};


window.openGroupRedPacketDialog = function(groupId) {
  const html = `
    <div style="padding:16px;">
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">红包类型</div>
        <select id="grp-rp-type" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff;">
          <option value="lucky">拼手气红包（金额随机）</option>
          <option value="normal">普通红包（金额均分）</option>
        </select>
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">红包总金额（积分）</div>
        <input id="grp-rp-total" type="number" value="10" min="1" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;">
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">红包个数</div>
        <input id="grp-rp-count" type="number" value="5" min="1" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;">
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">留言（可选）</div>
        <input id="grp-rp-msg" type="text" placeholder="恭喜发财，大吉大利" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;">
      </div>
      <div style="background:#fff7e6;border:1px solid #ffd591;border-radius:6px;padding:10px;margin-bottom:20px;font-size:12px;color:#874d00;line-height:1.6;">
        ⚠️ 红包 24 小时内有效，未领完的金额将退回你的积分账户。
      </div>
      <button id="grp-rp-submit" style="width:100%;padding:12px;background:#ef4444;color:#fff;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;">塞钱进红包</button>
    </div>
  `;
  window.openSubpage('发群红包', html);
  setTimeout(function() {
    const btn = document.getElementById('grp-rp-submit');
    if (!btn) return;
    btn.onclick = function() {
      const type = document.getElementById('grp-rp-type').value;
      const total = parseFloat(document.getElementById('grp-rp-total').value);
      const count = parseInt(document.getElementById('grp-rp-count').value);
      const msg = document.getElementById('grp-rp-msg').value || '';
      if (!total || total < 1) { alert('总金额最少 1'); return; }
      if (!count || count < 1) { alert('个数最少 1'); return; }
      fetch('/group/' + groupId + '/red-packets/create', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
        body: JSON.stringify({ total_amount: total, total_count: count, message: msg, source_type: 'user', packet_type: type })
      }).then(r => r.json()).then(data => {
        if (data.error || data.detail) { alert('发布失败：' + (data.error || data.detail)); return; }
        alert('红包已发送');
        if (typeof window.closeSubpage === 'function') window.closeSubpage();
        if (typeof loadGroupMessages === 'function') loadGroupMessages();
      }).catch(e => alert('网络错误：' + e.message));
    };
  }, 300);
};


async function loadGroupMessages() {
  try {
    const data = await api.getGroupMessages(currentGroupId);
    const messages = data.messages || [];
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    messages.forEach(msg => {
      const isSelf = (currentUserId != null && String(msg.sender_id) === String(currentUserId)) ||
                     (currentAgentId != null && String(msg.sender_agent_id) === String(currentAgentId));
      appendGroupMessage(msg.sender_name, msg.content, isSelf);
    });
  } catch (e) {
    appendGroupMessage('系统', '加载消息失败：' + e.message, false);
  }
}

function appendGroupMessage(senderName, content, isSelf = false) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;

  const wrapper = document.createElement('div');
  wrapper.className = `message-row ${isSelf ? 'user' : 'assistant'}`;

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = (senderName || '?').charAt(0).toUpperCase();

  const bubble = document.createElement('div');
  bubble.className = `message ${isSelf ? 'user' : 'assistant'}`;

  let _rendered = false;
  if (typeof content === 'string' && content.startsWith('[IMAGE]:')) {
    import('./chat_ui.js').then(m => {
      if (typeof m.renderImageBubble === 'function') {
        const node = m.renderImageBubble(content, isSelf ? 'user' : 'assistant', senderName);
        if (node && node.nodeType) messages.appendChild(node);
      }
    });
    bubble.style.display = 'none';
    _rendered = true;
  } else if (typeof content === 'string' && content.startsWith('[RED_PACKET]:')) {
    let _rp_data = {};
    try { _rp_data = JSON.parse(content.substring(13)); } catch (e) {}
    if (_rp_data.packet_id) {
      import('./chat_ui.js').then(m => {
        if (typeof m.renderGroupRedPacketBubble === 'function') {
          const node = m.renderGroupRedPacketBubble(content);
          if (node && node.nodeType) {
            bubble.innerHTML = '';
            bubble.style.padding = '0';
            bubble.style.background = 'transparent';
            bubble.style.border = 'none';
            bubble.appendChild(node);
          }
        }
      });
      _rendered = true;
    }

  } else if (typeof content === 'string' && content.startsWith('[RED_PACKET_DONE]:')) {
    import('./chat_ui.js').then(m => {
      if (typeof m.renderRedPacketDoneBubble === 'function') {
        const node = m.renderRedPacketDoneBubble(content);
        if (node && node.nodeType) {
          bubble.innerHTML = '';
          bubble.style.padding = '0';
          bubble.style.background = 'transparent';
          bubble.style.border = 'none';
          bubble.appendChild(node);
        }
      }
    });
    _rendered = true;

  } else if (typeof content === 'string' && content.startsWith('[TASK_CARD]:')) {
    import('./chat_ui.js').then(m => {
      if (typeof m.renderTaskCardBubble === 'function') {
        const node = m.renderTaskCardBubble(content);
        if (node && node.nodeType) {
          bubble.innerHTML = '';
          bubble.style.padding = '0';
          bubble.style.background = 'transparent';
          bubble.style.border = 'none';
          bubble.appendChild(node);
        }
      }
    });
    _rendered = true;
    import('./chat_ui.js').then(m => {
      if (typeof m.renderTaskCardBubble === 'function') {
        const node = m.renderTaskCardBubble(content);
        if (node && node.nodeType) {
          bubble.innerHTML = '';
          bubble.style.padding = '0';
          bubble.style.background = 'transparent';
          bubble.style.border = 'none';
          bubble.appendChild(node);
        }
      }
    });
    _rendered = true;
    import('./chat_ui.js').then(m => {
      if (typeof m.renderTaskCardBubble === 'function') {
        const node = m.renderTaskCardBubble(content);
        if (node && node.nodeType) messages.appendChild(node);
      }
    });
    bubble.style.display = 'none';
    _rendered = true;

  } else if (typeof content === 'string' && content.startsWith('[FILE]:')) {
    import('./chat_ui.js').then(m => {
      if (typeof m.renderFileBubble === 'function') {
        const node = m.renderFileBubble(content, isSelf ? 'user' : 'assistant', senderName);
        if (node && node.nodeType) messages.appendChild(node);
      }
    });
    bubble.style.display = 'none';
    _rendered = true;
  }
  if (!_rendered) {
    if (!isSelf) {
      bubble.innerHTML = `<span class="group-msg-sender">${senderName}:</span> ${content}`;
    } else {
      bubble.textContent = content;
    }
  }
  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);

  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

window.openPublishTaskDialog = function(groupId) {
  const html = `
    <div style="padding:16px;">
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">任务标题</div>
        <input id="pt-title" type="text" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;" placeholder="请输入标题">
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">任务描述</div>
        <textarea id="pt-desc" rows="3" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;resize:vertical;" placeholder="可选"></textarea>
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">任务类型</div>
        <select id="pt-category" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff;">
          <option value="text">文本</option>
          <option value="image">图片</option>
          <option value="code">代码</option>
          <option value="creative">创意</option>
        </select>
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">质押积分（最少 10）</div>
        <input id="pt-reward" type="number" value="10" min="10" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;">
      </div>
      <div style="background:#fff7e6;border:1px solid #ffd591;border-radius:6px;padding:10px;margin-bottom:20px;font-size:12px;color:#874d00;line-height:1.6;">
        ⚠️ 任务完成后，<b>95%</b> 给被选中的方案提交者，<b>5%</b> 进入群积分池。
      </div>
      <button id="pt-submit" style="width:100%;padding:12px;background:#07c160;color:#fff;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;">发布任务</button>
    </div>
  `;
  window.openSubpage('发布任务', html);
  setTimeout(function() {
    const btn = document.getElementById('pt-submit');
    if (!btn) return;
    btn.onclick = function() {
      const title = (document.getElementById('pt-title') || {}).value || '';
      const desc = (document.getElementById('pt-desc') || {}).value || '';
      const category = (document.getElementById('pt-category') || {}).value || 'text';
      const rewardStr = (document.getElementById('pt-reward') || {}).value || '0';
      if (!title.trim()) { alert('请输入标题'); return; }
      const reward = parseFloat(rewardStr);
      if (isNaN(reward) || reward < 10) { alert('质押积分最少 10'); return; }
      fetch('/group/' + groupId + '/tasks/publish', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim(), description: desc, category: category, reward: reward })
      }).then(r => r.json()).then(data => {
        if (data.error || data.detail) { alert('发布失败：' + (data.error || data.detail)); return; }
        alert('任务已发布');
        if (typeof window.closeSubpage === 'function') window.closeSubpage();
        if (typeof loadGroupMessages === 'function') loadGroupMessages();
      }).catch(e => alert('网络错误：' + e.message));
    };
  }, 300);
};


window.openTaskDetail = function(taskId) {
  fetch('/group/tasks/' + taskId, {
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
  }).then(r => r.json()).then(task => {
    if (task.error || task.detail) { alert('加载失败：' + (task.error || task.detail)); return; }
    const subs = task.submissions || [];
    const myId = parseInt(localStorage.getItem('sases_user_id') || '0');
    const isOwner = task.created_by === myId;
    const isOpen = task.status === 'open';
    let subHtml = '';
    if (subs.length === 0) {
      subHtml = '<div style="text-align:center;color:#999;padding:30px 0;">暂无提交</div>';
    } else {
      subs.forEach(s => {
        subHtml += '<div style="border:1px solid #eee;border-radius:8px;padding:12px;margin-bottom:10px;">';
        subHtml += '<div style="font-size:13px;color:#666;margin-bottom:6px;">' + (s.submitter_name || '匿名') + '</div>';
        subHtml += '<div style="font-size:14px;color:#333;word-break:break-all;white-space:pre-wrap;margin-bottom:8px;">' + (s.content || '') + '</div>';
        if (isOwner && isOpen) {
          subHtml += '<button class="pick-sub-btn" data-sid="' + s.id + '" style="padding:6px 14px;background:#07c160;color:#fff;border:none;border-radius:4px;font-size:13px;cursor:pointer;">选择此方案</button>';
        }
        subHtml += '</div>';
      });
    }
    let actionHtml = '';
    if (!isOwner && isOpen) {
      actionHtml = '<button id="td-submit-btn" style="width:100%;padding:12px;background:#07c160;color:#fff;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;margin-top:16px;">提交方案</button>';
    } else if (isOwner && isOpen && subs.length > 0) {
      actionHtml = '<div style="background:#fff7e6;border:1px solid #ffd591;border-radius:6px;padding:10px;margin-top:16px;font-size:12px;color:#874d00;">请在提交列表中点击"选择此方案"，未选择将超时退款。</div>';
    }
    const html = `
      <div style="padding:16px;">
        <div style="font-size:18px;font-weight:600;margin-bottom:8px;">${task.title || '未命名任务'}</div>
        <div style="font-size:13px;color:#666;margin-bottom:12px;">
          质押 ${task.reward_credits || 0} 积分 · 状态：${isOpen ? '进行中' : task.status}
        </div>
        <div style="background:#f8f8f8;border-radius:8px;padding:12px;margin-bottom:20px;font-size:14px;color:#333;white-space:pre-wrap;">${task.description || '（无描述）'}</div>
        <div style="font-size:15px;font-weight:600;margin-bottom:10px;">提交列表 (${subs.length})</div>
        ${subHtml}
        ${actionHtml}
      </div>
    `;
    window.openSubpage('任务详情', html);
    setTimeout(function() {
      const submitBtn = document.getElementById('td-submit-btn');
      if (submitBtn) {
        submitBtn.onclick = function() {
          const content = prompt('请输入你的方案（文字描述）：');
          if (!content) return;
          fetch('/group/tasks/' + taskId + '/submit', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content, content_type: 'text' })
          }).then(r => r.json()).then(data => {
            if (data.error || data.detail) { alert('提交失败：' + (data.error || data.detail)); return; }
            alert('提交成功');
            window.openTaskDetail(taskId);
          }).catch(e => alert('网络错误：' + e.message));
        };
      }
      document.querySelectorAll('.pick-sub-btn').forEach(btn => {
        btn.onclick = function() {
          const sid = btn.dataset.sid;
          if (!confirm('确定选择此方案？选定后 95% 质押积分将发给该提交者。')) return;
          fetch('/group/tasks/' + taskId + '/select', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({ submission_id: parseInt(sid) })
          }).then(r => r.json()).then(data => {
            if (data.error || data.detail) { alert('选择失败：' + (data.error || data.detail)); return; }
            alert('已选择，提交者获得 ' + data.winner_gets + ' 积分，群池 +' + data.pool_gets);
            window.openTaskDetail(taskId);
          }).catch(e => alert('网络错误：' + e.message));
        };
      });
    }, 100);
  }).catch(e => alert('网络错误：' + e.message));
};


export async function sendGroupMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  const atts = (window.chatState && Array.isArray(window.chatState.pendingAttachments)) ? [...window.chatState.pendingAttachments] : [];
  if (!text && atts.length === 0) return;
  if (!currentGroupId) return;
  try {
    for (const att of atts) {
      let content = '';
      if (att.type === 'image') {
        const res = await api.uploadImage(att.file);
        if (res && res.url) content = '[IMAGE]:' + res.url;
      } else {
        const res = await api.uploadFile(att.file);
        if (res && res.url) content = '[FILE]:' + res.url + '|' + att.name + '|' + att.size;
      }
      if (content) {
        await api.sendGroupMessage(currentGroupId, content, currentAgentId);
      }
    }
    if (text) {
      await api.sendGroupMessage(currentGroupId, text, currentAgentId);
    }
    if (window.chatState) window.chatState.pendingAttachments = [];
    if (window.__sasesClearAttachment) window.__sasesClearAttachment();
    input.value = '';
    loadGroupMessages();
  } catch (e) {
    alert('发送失败：' + (e.message || '未知错误'));
  }
}

// ==================== 群模式切换（下拉菜单） ====================
function openGroupModeMenu() {
  const menu = document.getElementById('mode-menu');
  const content = document.getElementById('mode-menu-content');
  if (!menu || !content) return;

  content.innerHTML = `
    <div class="plus-menu-item mode-item ${currentGroupMode === 'normal' ? 'active-mode' : ''}" data-mode="normal">
      <span class="plus-menu-label">普通聊天</span>
    </div>
    <div class="plus-menu-item mode-item ${currentGroupMode === 'swarm' ? 'active-mode' : ''}" data-mode="swarm">
      <span class="plus-menu-label">蜂群模式</span>
    </div>
  `;

  const modeBtn = document.getElementById('chat-mode-btn');
  if (modeBtn) {
    const rect = modeBtn.getBoundingClientRect();
    content.style.left = rect.left + 'px';
    content.style.top = (rect.bottom + 5) + 'px';
    content.style.position = 'fixed';
  }

  menu.style.display = 'block';
  document.getElementById('mode-menu-overlay').onclick = closeGroupModeMenu;

  content.querySelectorAll('.mode-item').forEach(el => {
    el.addEventListener('click', async () => {
      const mode = el.dataset.mode;
      await applyGroupMode(mode);
      closeGroupModeMenu();
    });
  });
}

function closeGroupModeMenu() {
  document.getElementById('mode-menu').style.display = 'none';
}

async function applyGroupMode(mode) {
  try {
    await api.setGroupMode(currentGroupId, mode);
    currentGroupMode = mode;
    const modeText = document.getElementById('chat-mode-text');
    if (modeText) modeText.textContent = mode === 'normal' ? '普通聊天' : '蜂群模式';
    if (mode === 'swarm') {
      alert('蜂群模式暂未开放任务功能，仅可切换回普通聊天。');
    }
  } catch (e) {
    alert('切换失败：' + e.message);
  }
}

async function openGroupSettings() {
  const contentHtml = `
    <div class="group-settings-container">
      <div class="member-grid" id="group-members-container"><div class="subpage-placeholder">加载中...</div></div>
      <div class="me-menu">
        <div class="me-menu-item"><span class="menu-label">群聊名称</span><span class="menu-value">${currentGroupName}</span></div>
        <div class="me-menu-item" id="identity-switch-entry"><span class="menu-label">身份切换</span><span class="menu-value" id="identity-current">以本人身份</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="group-mode-entry"><span class="menu-label">群模式</span><span class="menu-value" id="group-mode-current">${currentGroupMode === 'normal' ? '普通聊天' : '蜂群模式'}</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="announcement-entry"><span class="menu-label">群公告</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="nickname-entry"><span class="menu-label">我在本群的昵称</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="search-history-entry"><span class="menu-label">查找聊天记录</span><span class="menu-arrow">›</span></div>
      </div>
      <div class="me-menu">
        <div class="me-menu-item" id="mute-entry"><span class="menu-label">消息免打扰</span><div class="switch" id="mute-switch"><div class="slider"></div></div></div>
        <div class="me-menu-item" id="pin-entry"><span class="menu-label">置顶聊天</span><div class="switch" id="pin-switch"><div class="slider"></div></div></div>
      </div>
      <div class="me-menu">
        <div class="me-menu-item" id="group-credits-entry"><span class="menu-label">群积分</span><span class="menu-value" id="group-credits-balance">0</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="group-leaderboard-entry"><span class="menu-label">群排行榜</span><span class="menu-arrow">›</span></div>
      </div>
      <div class="me-menu">
        <div class="me-menu-item" id="clear-history-entry"><span class="menu-label">清空聊天记录</span></div>
        <div class="me-menu-item danger" id="leave-group-entry"><span class="menu-label">退出群聊</span></div>
      </div>
    </div>
  `;
  window.openSubpage('群设置', contentHtml, { showMore: false });

  loadGroupCredits();
  await loadGroupMembers();

  const identityEntry = document.getElementById('identity-switch-entry');
  if (identityEntry) identityEntry.addEventListener('click', openAgentSwitch);

  const groupModeEntry = document.getElementById('group-mode-entry');
  if (groupModeEntry) groupModeEntry.addEventListener('click', openGroupModeMenu);

  const announcementEntry = document.getElementById('announcement-entry');
  if (announcementEntry) announcementEntry.addEventListener('click', openAnnouncementEditor);

  const nicknameEntry = document.getElementById('nickname-entry');
  if (nicknameEntry) nicknameEntry.addEventListener('click', openNicknameEditor);

  const searchHistoryEntry = document.getElementById('search-history-entry');
  if (searchHistoryEntry) searchHistoryEntry.addEventListener('click', openGroupSearch);

  const muteEntry = document.getElementById('mute-entry');
  if (muteEntry) muteEntry.addEventListener('click', toggleGroupMute);

  const pinEntry = document.getElementById('pin-entry');
  if (pinEntry) pinEntry.addEventListener('click', toggleGroupPin);

  const groupCreditsEntry = document.getElementById('group-credits-entry');
  if (groupCreditsEntry) groupCreditsEntry.addEventListener('click', openGroupCreditsDetail);

  const groupLeaderboardEntry = document.getElementById('group-leaderboard-entry');
  if (groupLeaderboardEntry) groupLeaderboardEntry.addEventListener('click', openGroupLeaderboard);

  const clearHistoryEntry = document.getElementById('clear-history-entry');
  if (clearHistoryEntry) clearHistoryEntry.addEventListener('click', clearGroupHistory);

  const leaveGroupEntry = document.getElementById('leave-group-entry');
  if (leaveGroupEntry) leaveGroupEntry.addEventListener('click', leaveGroup);
}

async function loadGroupCredits() {
  try {
    const data = await api.getGroupCredits(currentGroupId);
    const credits = data.credits || 0;
    document.getElementById('group-credits-balance').textContent = credits;
  } catch (e) {
    document.getElementById('group-credits-balance').textContent = '0';
  }
}

async function loadGroupMembers() {
  try {
    const data = await api.getGroupMembers(currentGroupId);
    const members = data.members || [];
    const container = document.getElementById('group-members-container');
    let html = '';
    members.forEach(member => {
      const icon = member.member_type === 'agent' ? '🤖' : '👤';
      const displayName = member.display_name || '成员';
      html += `
        <div class="member-grid-item" data-user-id="${member.user_id || ''}" data-agent-id="${member.agent_id || ''}">
          <div class="member-grid-avatar">${icon}</div>
          <div class="member-grid-name">${displayName}</div>
        </div>
      `;
    });
    html += `
      <div class="member-grid-item member-grid-action" id="invite-member-btn"><div class="member-grid-avatar action">＋</div><div class="member-grid-name">邀请</div></div>
      <div class="member-grid-item member-grid-action" id="remove-member-btn"><div class="member-grid-avatar action">－</div><div class="member-grid-name">移除</div></div>
    `;
    container.innerHTML = html;
    const inviteBtn = document.getElementById('invite-member-btn');
    if (inviteBtn) inviteBtn.addEventListener('click', openInviteDialog);
    const removeBtn = document.getElementById('remove-member-btn');
    if (removeBtn) removeBtn.addEventListener('click', openRemoveDialog);
  } catch (e) {
    document.getElementById('group-members-container').innerHTML = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }
}

function openInviteDialog() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">用户名 / SASES ID / 智能体 ID</span>
        <input type="text" id="invite-input" class="inline-input" placeholder="输入用户名、SASES ID 或智能体 ID">
      </div>
    </div>
    <button class="save-btn" id="confirm-invite-btn">邀请</button>
  `;
  window.openSubpage('邀请成员', contentHtml);

  setTimeout(() => {
    document.getElementById('confirm-invite-btn').addEventListener('click', async () => {
      const input = document.getElementById('invite-input').value.trim();
      if (!input) { alert('请输入用户名或 ID'); return; }
      try {
        await api.inviteToGroup(currentGroupId, input);
        alert('邀请成功');
        window.closeSubpage();
        openGroupSettings();
      } catch (e) {
        alert('邀请失败：' + e.message);
      }
    });
  }, 300);
}

function openRemoveDialog() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">输入要移除的成员 ID 或名称</span>
        <input type="text" id="remove-input" class="inline-input" placeholder="输入用户 ID 或智能体 ID">
      </div>
    </div>
    <button class="save-btn" id="confirm-remove-btn" style="background:#ff3b30;">移除</button>
  `;
  window.openSubpage('移除成员', contentHtml);

  setTimeout(() => {
    document.getElementById('confirm-remove-btn').addEventListener('click', async () => {
      const input = document.getElementById('remove-input').value.trim();
      if (!input) { alert('请输入成员标识'); return; }
      try {
        await api.removeGroupMember(currentGroupId, input);
        alert('移除成功');
        window.closeSubpage();
        openGroupSettings();
      } catch (e) {
        alert('移除失败：' + e.message);
      }
    });
  }, 300);
}

async function openAgentSwitch() {
  const contentHtml = `
    <div class="me-menu" id="agent-switch-list">
      <div class="me-menu-item agent-option" data-agent-id="">👤 以本人身份</div>
      <div class="subpage-placeholder">加载智能体...</div>
    </div>
  `;
  window.openSubpage('选择发言身份', contentHtml);

  try {
    const data = await api.listMyAgents();
    const agents = data.agents || [];
    const container = document.getElementById('agent-switch-list');
    if (agents.length === 0) {
      container.innerHTML = '<div class="subpage-placeholder">暂无智能体</div>';
      return;
    }
    let html = '<div class="me-menu-item agent-option" data-agent-id="">👤 以本人身份</div>';
    agents.forEach(agent => {
      html += `
        <div class="me-menu-item agent-option" data-agent-id="${agent.agent_id}">
          <span class="menu-icon">🤖</span>
          ${agent.name}
        </div>
      `;
    });
    container.innerHTML = html;

    container.querySelectorAll('.agent-option').forEach(opt => {
      opt.addEventListener('click', () => {
        currentAgentId = opt.dataset.agentId || null;
        window.closeSubpage();
        document.getElementById('chat-window-title').textContent = currentGroupName + (currentAgentId ? ' (智能体)' : '');
        openGroupSettings();
      });
    });
  } catch (e) {
    document.getElementById('agent-switch-list').innerHTML = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }
}

function openAnnouncementEditor() { alert('群公告编辑开发中'); }
function openNicknameEditor() { alert('昵称编辑开发中'); }
function openGroupSearch() { alert('查找聊天记录开发中'); }
function toggleGroupMute() { alert('免打扰开发中'); }
function toggleGroupPin() {
  api.togglePinGroup(currentGroupId, true).then(() => location.reload()).catch(e => alert('操作失败: ' + e.message));
}
async function openGroupCreditsDetail() {
  let pool = { available: 0, staked: 0, total: 0, red_packet_hour: 20, red_packet_audience: 'all' };
  try {
    const resp = await fetch('/group/' + currentGroupId + '/pool', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    pool = await resp.json();
  } catch (e) {}
  const contentHtml = `
    <div class="wallet-card" style="background: linear-gradient(135deg, #007aff, #00c6ff);">
      <div class="wallet-label">可用积分</div>
      <div class="wallet-balance">${pool.available || 0}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:4px;">用于发任务、发红包</div>
    </div>
    <div class="wallet-card" style="background: linear-gradient(135deg, #667eea, #764ba2);">
      <div class="wallet-label">质押总额</div>
      <div class="wallet-balance">${pool.staked || 0}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:4px;">锁定期 30 天，到期可提取</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="gc-stake-entry">
        <span class="menu-icon">💰</span>
        <span class="menu-label">质押积分</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item">
        <span class="menu-icon">📊</span>
        <span class="menu-label">总积分</span>
        <span class="menu-value">${pool.total || 0}</span>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="gc-redpacket-config">
        <span class="menu-icon">🧧</span>
        <span class="menu-label">红包配置</span>
        <span class="menu-value">${pool.red_packet_hour || 20}:00</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="gc-send-redpacket">
        <span class="menu-icon">🎁</span>
        <span class="menu-label">立即发红包（群主）</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
    <div class="section-title">积分说明</div>
    <div style="padding:12px;font-size:13px;color:#666;line-height:1.8;">
      • 任务抽成 5% 进入群池<br>
      • 每日空投按活跃度竞争（10000 分/天）<br>
      • 可用余额满 1000 可发群红包
    </div>
  `;
  window.openSubpage('群积分', contentHtml, { showMore: false });
  setTimeout(() => {
    const stake = document.getElementById('gc-stake-entry');
    if (stake) stake.onclick = openGroupStakeDialog;
    const config = document.getElementById('gc-redpacket-config');
    if (config) config.onclick = openRedPacketConfig;
    const send = document.getElementById('gc-send-redpacket');
    if (send) send.onclick = sendRedPacketNow;
  }, 300);
}

function openGroupStakeDialog() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">质押金额（最少 10）</span>
        <input type="number" id="gc-stake-amount" class="inline-input" value="10" min="10">
      </div>
    </div>
    <div style="padding:12px;font-size:12px;color:#666;line-height:1.6;">
      质押积分锁定 30 天，到期后可提取。质押后该群获得空投资格（需总积分≥100）。
    </div>
    <button class="save-btn" id="gc-stake-submit">质押</button>
  `;
  window.openSubpage('质押积分', contentHtml);
  setTimeout(() => {
    const btn = document.getElementById('gc-stake-submit');
    if (!btn) return;
    btn.onclick = async () => {
      const amount = parseFloat(document.getElementById('gc-stake-amount').value);
      if (!amount || amount < 10) { alert('最少质押 10'); return; }
      try {
        const resp = await fetch('/group/' + currentGroupId + '/stake', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount: amount })
        });
        const data = await resp.json();
        if (data.error || data.detail) { alert('质押失败：' + (data.error || data.detail)); return; }
        alert('质押成功');
        window.closeSubpage();
        openGroupCreditsDetail();
      } catch (e) { alert('网络错误：' + e.message); }
    };
  }, 300);
}

function openRedPacketConfig() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">发放时间（0-23 点）</span>
        <input type="number" id="gc-rp-hour" class="inline-input" value="20" min="0" max="23">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">谁可以抢</span>
        <select id="gc-rp-audience" class="inline-input">
          <option value="all">所有群成员</option>
          <option value="stakers">仅质押成员</option>
        </select>
      </div>
    </div>
    <button class="save-btn" id="gc-rp-save">保存配置</button>
  `;
  window.openSubpage('红包配置', contentHtml);
  setTimeout(() => {
    const btn = document.getElementById('gc-rp-save');
    if (!btn) return;
    btn.onclick = async () => {
      const hour = parseInt(document.getElementById('gc-rp-hour').value);
      const audience = document.getElementById('gc-rp-audience').value;
      if (isNaN(hour) || hour < 0 || hour > 23) { alert('小时必须 0-23'); return; }
      try {
        const resp = await fetch('/group/' + currentGroupId + '/red-packet/config', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
          body: JSON.stringify({ hour: hour, audience: audience })
        });
        const data = await resp.json();
        if (data.error || data.detail) { alert('保存失败：' + (data.error || data.detail)); return; }
        alert('已保存');
        window.closeSubpage();
        openGroupCreditsDetail();
      } catch (e) { alert('网络错误：' + e.message); }
    };
  }, 300);
}

function sendRedPacketNow() {
  if (!confirm('确定立即发放群红包？群池可用余额将均分给符合受众的成员。')) return;
  fetch('/group/' + currentGroupId + '/red-packet/send', {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
  }).then(r => r.json()).then(data => {
    if (data.error || data.detail) { alert('发放失败：' + (data.error || data.detail)); return; }
    alert('已发放 ' + data.total + ' 积分给 ' + data.recipients + ' 人');
    window.closeSubpage();
    openGroupCreditsDetail();
  }).catch(e => alert('网络错误：' + e.message));
}



function openGroupLeaderboard() { alert('群排行榜开发中'); }
function clearGroupHistory() {
  if (!confirm('确定清空本群聊天记录（仅你的视角）？')) return;
  alert('清空功能开发中');
}
function leaveGroup() {
  if (!confirm('确定退出群聊？')) return;
  api.removeGroupMember(currentGroupId, 'self').then(() => { window.closeSubpage(); location.reload(); }).catch(e => alert('失败: ' + e.message));
}