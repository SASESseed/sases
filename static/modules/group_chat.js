// static/modules/group_chat.js
import { api } from './api.js';

let currentGroupId = null;
let currentGroupName = '';
let currentAgentId = null;

export function openGroupChat(groupId, groupName) {
  currentGroupId = groupId;
  currentGroupName = groupName;
  currentAgentId = null;

  const titleEl = document.getElementById('chat-window-title');
  const viewEl = document.getElementById('view-chat-window');
  const bottomNav = document.querySelector('.bottom-nav');
  const topBar = document.querySelector('.top-bar');
  const settingsBtn = document.getElementById('group-settings-btn');
  const messagesContainer = document.getElementById('chat-messages');

  if (titleEl) titleEl.textContent = groupName;
  if (viewEl) viewEl.style.display = 'flex';
  if (bottomNav) bottomNav.style.display = 'none';
  if (topBar) topBar.style.display = 'none';
  if (settingsBtn) {
    settingsBtn.style.display = 'block';
    settingsBtn.onclick = openGroupSettings;
  }

  if (messagesContainer) messagesContainer.innerHTML = '';
  loadGroupMessages();
}

export function closeGroupChat() {
  currentGroupId = null;
  currentGroupName = '';
  currentAgentId = null;
  window.currentGroupOwner = false;

  const viewEl = document.getElementById('view-chat-window');
  const bottomNav = document.querySelector('.bottom-nav');
  const topBar = document.querySelector('.top-bar');
  const settingsBtn = document.getElementById('group-settings-btn');
  const messagesContainer = document.getElementById('chat-messages');

  if (viewEl) viewEl.style.display = 'none';
  if (bottomNav) bottomNav.style.display = 'flex';
  if (topBar) topBar.style.display = 'flex';
  if (settingsBtn) settingsBtn.style.display = 'none';
  if (messagesContainer) messagesContainer.innerHTML = '';
}

async function fetchGroupRole() {
  try {
    const data = await api.getGroupInfo(currentGroupId);
    const ownerId = data.owner_id;
    const myUserId = parseInt(localStorage.getItem('sases_user_id') || '0');
    window.currentGroupOwner = (ownerId === myUserId);
  } catch (e) {
    window.currentGroupOwner = false;
  }
}

// ==================== 群设置 ====================
async function openGroupSettings() {
  // 先获取群角色，确保任务模式入口正确
  await fetchGroupRole();

  const contentHtml = `
    <div class="group-settings-container">
      <div class="wallet-card" style="margin-bottom:16px;">
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

  const inviteBtn = document.getElementById('invite-member-btn');
  if (inviteBtn) inviteBtn.addEventListener('click', openInviteDialog);

  const removeBtn = document.getElementById('remove-member-btn');
  if (removeBtn) removeBtn.addEventListener('click', openRemoveDialog);
}

async function loadGroupCredits() {
  const balanceEl = document.getElementById('group-credits-balance');
  if (!balanceEl) return;
  try {
    const data = await api.getGroupCredits(currentGroupId);
    balanceEl.textContent = data.credits || 0;
  } catch (e) {
    balanceEl.textContent = '0';
  }
}

async function loadGroupMembers() {
  const container = document.getElementById('group-members-container');
  if (!container) return;
  try {
    const data = await api.getGroupMembers(currentGroupId);
    const members = data.members || [];
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
    container.innerHTML = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
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
    const input = document.getElementById('invite-input');
    const btn = document.getElementById('confirm-invite-btn');
    if (!input || !btn) return;

    btn.addEventListener('click', async () => {
      const value = input.value.trim();
      if (!value) { alert('请输入用户名或 ID'); return; }
      try {
        await api.inviteToGroup(currentGroupId, value);
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
    const input = document.getElementById('remove-input');
    const btn = document.getElementById('confirm-remove-btn');
    if (!input || !btn) return;

    btn.addEventListener('click', async () => {
      const value = input.value.trim();
      if (!value) { alert('请输入成员标识'); return; }
      try {
        await api.removeGroupMember(currentGroupId, value);
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
    if (!container) return;

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
        const titleEl = document.getElementById('chat-window-title');
        if (titleEl) titleEl.textContent = currentGroupName + (currentAgentId ? ' (智能体)' : '');
      });
    });
  } catch (e) {
    const container = document.getElementById('agent-switch-list');
    if (container) container.innerHTML = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }
}

// ==================== 消息加载与发送 ====================
async function loadGroupMessages() {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  try {
    const data = await api.getGroupMessages(currentGroupId);
    const messages = data.messages || [];
    container.innerHTML = '';
    messages.forEach(msg => {
      appendGroupMessage(msg.sender_name, msg.content);
    });
  } catch (e) {
    appendGroupMessage('系统', '加载消息失败：' + e.message);
  }
}

function appendGroupMessage(senderName, content) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;
  const div = document.createElement('div');
  div.className = 'message group-message';
  div.innerHTML = `<span class="group-msg-sender">${senderName}:</span> ${content}`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

export async function sendGroupMessage() {
  const input = document.getElementById('chat-input');
  if (!input) return;
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