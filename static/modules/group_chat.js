// static/modules/group_chat.js
import { api } from './api.js';
import { t } from './i18n.js';

let currentGroupId = null;
let currentGroupName = '';
let currentAgentId = null;
let currentMode = 'normal';

export function openGroupChat(groupId, groupName) {
  currentGroupId = groupId;
  currentGroupName = groupName;
  currentAgentId = null;
  currentMode = 'normal';

  document.getElementById('chat-window-title').textContent = groupName;
  document.getElementById('view-chat-window').style.display = 'flex';
  document.querySelector('.bottom-nav').style.display = 'none';
  document.querySelector('.top-bar').style.display = 'none';

  const settingsBtn = document.getElementById('group-settings-btn');
  if (settingsBtn) {
    settingsBtn.style.display = 'block';
    settingsBtn.onclick = openGroupSettings;
  }

  fetchGroupRole();

  const messagesContainer = document.getElementById('chat-messages');
  messagesContainer.innerHTML = '';
  loadGroupMessages();
}

export function closeGroupChat() {
  currentGroupId = null;
  currentGroupName = '';
  currentAgentId = null;
  currentMode = 'normal';
  window.currentGroupOwner = false;
  document.getElementById('view-chat-window').style.display = 'none';
  document.querySelector('.bottom-nav').style.display = 'flex';
  document.querySelector('.top-bar').style.display = 'flex';
  const settingsBtn = document.getElementById('group-settings-btn');
  if (settingsBtn) settingsBtn.style.display = 'none';
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

// ==================== 群设置页面 ====================
async function openGroupSettings() {
  const contentHtml = `
    <div class="group-settings-container">
      <div class="wallet-card" id="group-credits-card" style="margin-bottom:16px;">
        <div class="wallet-label">${t('group_credits')}</div>
        <div class="wallet-balance" id="group-credits-balance">0</div>
      </div>
      <div class="me-menu">
        <div class="me-menu-item">
          <span class="menu-label">${t('group_name')}</span>
          <span class="menu-value">${currentGroupName}</span>
        </div>
        <div class="me-menu-item" id="identity-switch-entry">
          <span class="menu-label">${t('identity_switch')}</span>
          <span class="menu-value" id="identity-current">${t('self_identity')}</span>
          <span class="menu-arrow">›</span>
        </div>
      </div>
      <div class="section-title">${t('group_members')}</div>
      <div id="group-members-container" class="me-menu">
        <div class="subpage-placeholder">${t('loading')}...</div>
      </div>
      <div style="display:flex; gap:8px; margin-top:12px;">
        <button id="invite-member-btn" class="save-btn" style="flex:1;">${t('invite_member')}</button>
        <button id="remove-member-btn" class="save-btn" style="flex:1; background:#ff3b30;">${t('remove_member')}</button>
      </div>
    </div>
  `;
  window.openSubpage(t('group_settings'), contentHtml, { showMore: false });

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
      container.innerHTML = `<div class="subpage-placeholder">${t('no_members')}</div>`;
      return;
    }
    let html = '';
    members.forEach(member => {
      const icon = member.member_type === 'agent' ? '🤖' : '👤';
      const displayName = member.display_name;
      const role = member.role === 'owner' ? t('owner') : (member.role === 'agent' ? t('agent') : t('member'));
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
    document.getElementById('group-members-container').innerHTML = `<div class="subpage-placeholder">${t('load_failed')}: ${e.message}</div>`;
  }
}

function openInviteDialog() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">${t('username_or_id')}</span>
        <input type="text" id="invite-input" class="inline-input" placeholder="${t('enter_username_or_id')}">
      </div>
    </div>
    <button class="save-btn" id="confirm-invite-btn">${t('invite')}</button>
  `;
  window.openSubpage(t('invite_member'), contentHtml);

  setTimeout(() => {
    document.getElementById('confirm-invite-btn').addEventListener('click', async () => {
      const input = document.getElementById('invite-input').value.trim();
      if (!input) { alert(t('please_input_all')); return; }
      try {
        await api.inviteToGroup(currentGroupId, input);
        alert(t('invite_success'));
        window.closeSubpage();
        openGroupSettings();
      } catch (e) {
        alert(t('invite_failed') + ': ' + e.message);
      }
    });
  }, 100);
}

function openRemoveDialog() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">${t('username_or_id')}</span>
        <input type="text" id="remove-input" class="inline-input" placeholder="${t('enter_username_or_id')}">
      </div>
    </div>
    <button class="save-btn" id="confirm-remove-btn" style="background:#ff3b30;">${t('remove')}</button>
  `;
  window.openSubpage(t('remove_member'), contentHtml);

  setTimeout(() => {
    document.getElementById('confirm-remove-btn').addEventListener('click', async () => {
      const input = document.getElementById('remove-input').value.trim();
      if (!input) { alert(t('please_input_all')); return; }
      try {
        await api.removeGroupMember(currentGroupId, input);
        alert(t('remove_success'));
        window.closeSubpage();
        openGroupSettings();
      } catch (e) {
        alert(t('remove_failed') + ': ' + e.message);
      }
    });
  }, 100);
}

async function openAgentSwitch() {
  const contentHtml = `
    <div class="me-menu" id="agent-switch-list">
      <div class="me-menu-item agent-option" data-agent-id="">👤 ${t('self_identity')}</div>
      <div class="subpage-placeholder">${t('loading')}...</div>
    </div>
  `;
  window.openSubpage(t('identity_switch'), contentHtml);

  try {
    const data = await api.listMyAgents();
    const agents = data.agents || [];
    const container = document.getElementById('agent-switch-list');
    if (agents.length === 0) {
      container.innerHTML = `<div class="subpage-placeholder">${t('no_agents')}</div>`;
      return;
    }
    let html = `<div class="me-menu-item agent-option" data-agent-id="">👤 ${t('self_identity')}</div>`;
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
    document.getElementById('agent-switch-list').innerHTML = `<div class="subpage-placeholder">${t('load_failed')}: ${e.message}</div>`;
  }
}

// ==================== 消息加载与发送 ====================
async function loadGroupMessages() {
  try {
    const data = await api.getGroupMessages(currentGroupId);
    const messages = data.messages || [];
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    messages.forEach(msg => {
      appendGroupMessage(msg.sender_name, msg.content);
    });
  } catch (e) {
    appendGroupMessage('系统', `${t('load_failed')}: ${e.message}`);
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
  const text = input.value.trim();
  if (!text || !currentGroupId) return;
  try {
    await api.sendGroupMessage(currentGroupId, text, currentAgentId);
    input.value = '';
    loadGroupMessages();
  } catch (e) {
    alert(t('send_failed') + ': ' + e.message);
  }
}