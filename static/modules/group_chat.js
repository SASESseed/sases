// static/modules/group_chat.js
import { api } from './api.js';

let currentGroupId = null;
let currentGroupName = '';
let currentAgentId = null; // 当前使用的智能体身份，null 表示用户本人
let currentGroupMode = 'normal'; // normal 或 swarm
let currentUserId = null; // 当前登录用户ID

export function openGroupChat(groupId, groupName) {
  currentGroupId = groupId;
  currentGroupName = groupName;
  currentAgentId = null;
  currentGroupMode = 'normal';
  window.currentGroupChat = true;

  // 获取当前用户ID，用于消息左右布局判断
  api.getMe().then(data => {
    currentUserId = data.user_id;
  }).catch(() => {
    currentUserId = null;
  });

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

  const messagesContainer = document.getElementById('chat-messages');
  messagesContainer.innerHTML = '';
  loadGroupMessages();
}

export function closeGroupChat() {
  currentGroupId = null;
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

async function loadGroupMessages() {
  try {
    const data = await api.getGroupMessages(currentGroupId);
    const messages = data.messages || [];
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    messages.forEach(msg => {
      const isSelf = (currentUserId !== null && msg.sender_id === currentUserId) ||
                     (currentAgentId !== null && msg.sender_agent_id === currentAgentId);
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

  if (!isSelf) {
    bubble.innerHTML = `<span class="group-msg-sender">${senderName}:</span> ${content}`;
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
  } else {
    bubble.textContent = content;
    wrapper.appendChild(bubble);
    wrapper.appendChild(avatar);
  }

  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

export async function sendGroupMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text || !currentGroupId) return;
  try {
    await api.sendGroupMessage(currentGroupId, text, currentAgentId);
    input.value = '';
    loadGroupMessages();
  } catch (e) {
    alert('发送失败：' + e.message);
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
      <div class="wallet-card" id="group-credits-card" style="margin-bottom:16px;">
        <div class="wallet-label">群积分</div>
        <div class="wallet-balance" id="group-credits-balance">0</div>
      </div>
      <div class="me-menu">
        <div class="me-menu-item">
          <span class="menu-label">群名称</span>
          <span class="menu-value">${currentGroupName}</span>
        </div>
        <div class="me-menu-item" id="identity-switch-entry">
          <span class="menu-label">身份切换</span>
          <span class="menu-value" id="identity-current">以本人身份</span>
          <span class="menu-arrow">›</span>
        </div>
        <div class="me-menu-item" id="group-mode-entry">
          <span class="menu-label">群模式</span>
          <span class="menu-value" id="group-mode-current">${currentGroupMode === 'normal' ? '普通聊天' : '蜂群模式'}</span>
          <span class="menu-arrow">›</span>
        </div>
      </div>
      <div class="section-title">群成员</div>
      <div id="group-members-container" class="me-menu">
        <div class="subpage-placeholder">加载中...</div>
      </div>
      <div style="display:flex; gap:8px; margin-top:12px;">
        <button id="invite-member-btn" class="save-btn" style="flex:1;">邀请成员</button>
        <button id="remove-member-btn" class="save-btn" style="flex:1; background:#ff3b30;">移除成员</button>
      </div>
    </div>
  `;
  window.openSubpage('群设置', contentHtml, { showMore: false });

  loadGroupCredits();
  loadGroupMembers();

  const identityEntry = document.getElementById('identity-switch-entry');
  if (identityEntry) identityEntry.addEventListener('click', openAgentSwitch);

  const groupModeEntry = document.getElementById('group-mode-entry');
  if (groupModeEntry) groupModeEntry.addEventListener('click', openGroupModeMenu);

  const inviteBtn = document.getElementById('invite-member-btn');
  if (inviteBtn) inviteBtn.addEventListener('click', openInviteDialog);

  const removeBtn = document.getElementById('remove-member-btn');
  if (removeBtn) removeBtn.addEventListener('click', openRemoveDialog);
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
    if (members.length === 0) {
      container.innerHTML = '<div class="subpage-placeholder">暂无成员</div>';
      return;
    }
    let html = '';
    members.forEach(member => {
      const icon = member.member_type === 'agent' ? '🤖' : '👤';
      const displayName = member.display_name;
      const role = member.role === 'owner' ? '群主' : (member.role === 'agent' ? '智能体' : '成员');
      html += `
        <div class="me-menu-item member-item">
          <span class="menu-icon">${icon}</span>
          <div class="menu-text">
            <div class="menu-title">${displayName}</div>
            <div class="menu-desc">${role}</div>
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
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
  }, 100);
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
  }, 100);
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