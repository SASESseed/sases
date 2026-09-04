// static/modules/chat.js
import { api } from './api.js';
import { t } from './i18n.js';
import { closeGroupChat, sendGroupMessage } from './group_chat.js';
import { createContextMenu, attachLongPress, closeContextMenu, getPendingQuote, clearPendingQuote } from './message_actions.js';
import { toggleChatPlusPanel, closeChatPlusPanel } from './chat_plus_panel.js';

let chatInitialized = false;
let currentConversationId = null;
let currentAgentId = null;
let currentAgentType = 'my';
let currentSenderAgentId = null;
let currentMode = 'free';
let isVoiceMode = false;
let lastMessageTime = null;
let lastMessageId = 0;
let pollingTimer = null;

const PAGE_SIZE = 50;
let currentOffset = 0;
let isLoadingMore = false;
let hasMoreMessages = true;

export function initChat() {
  const sendBtn = document.getElementById('send-btn');
  const input = document.getElementById('chat-input');
  const backBtn = document.getElementById('chat-back-btn');
  const infoBtn = document.getElementById('chat-info-btn');
  const modeBtn = document.getElementById('chat-mode-btn');
  const toggleVoiceBtn = document.getElementById('toggle-voice-btn');
  const identityBtn = document.getElementById('identity-btn');
  const inputPlusBtn = document.getElementById('input-plus-btn');
  const messagesContainer = document.getElementById('chat-messages');

  if (!sendBtn || !input || !backBtn || !infoBtn || !modeBtn || chatInitialized) return;
  chatInitialized = true;

  sendBtn.addEventListener('click', handleSend);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });
  input.addEventListener('input', updateSendButtonVisibility);

  backBtn.addEventListener('click', handleBack);
  infoBtn.addEventListener('click', openChatInfo);
  modeBtn.addEventListener('click', openModeMenu);
  toggleVoiceBtn.addEventListener('click', toggleVoiceMode);
  identityBtn.addEventListener('click', openIdentitySwitch);
  inputPlusBtn.addEventListener('click', toggleChatPlusPanel);

  if (messagesContainer) {
    messagesContainer.addEventListener('scroll', handleScroll);
  }

  updateSendButtonVisibility();
  createContextMenu();
}

function handleSend() {
  if (window.currentGroupChat) {
    sendGroupMessage();
  } else {
    sendMessage();
  }
}

function handleBack() {
  if (window.currentGroupChat) {
    closeGroupChat();
    window.currentGroupChat = false;
  } else {
    closeChatWindow();
  }
}

function updateSendButtonVisibility() {
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const plusBtn = document.getElementById('input-plus-btn');
  if (!input || !sendBtn || !plusBtn) return;

  if (input.value.trim().length > 0) {
    sendBtn.style.display = 'block';
    plusBtn.style.display = 'none';
  } else {
    sendBtn.style.display = 'none';
    plusBtn.style.display = 'block';
  }
}

function toggleVoiceMode() {
  const input = document.getElementById('chat-input');
  const toggleBtn = document.getElementById('toggle-voice-btn');
  if (!input || !toggleBtn) return;

  isVoiceMode = !isVoiceMode;
  if (isVoiceMode) {
    input.style.display = 'none';
    toggleBtn.textContent = '⌨️';
    input.placeholder = t('input_placeholder');
  } else {
    input.style.display = 'block';
    toggleBtn.textContent = '🎤';
    input.placeholder = t('input_placeholder');
  }
}

export function openChatWindow(conversationId, chatName, agentId = null, agentType = 'my') {
  currentConversationId = conversationId ? parseInt(conversationId) : null;
  currentAgentId = agentId;
  currentAgentType = agentType;
  currentSenderAgentId = null;
  currentMode = 'free';
  lastMessageTime = null;
  lastMessageId = 0;
  currentOffset = 0;
  isLoadingMore = false;
  hasMoreMessages = true;

  updateModeText();

  const titleEl = document.getElementById('chat-window-title');
  if (titleEl) titleEl.textContent = chatName || '会话';

  document.getElementById('view-chat-window').style.display = 'flex';
  document.querySelector('.bottom-nav').style.display = 'none';
  document.querySelector('.top-bar').style.display = 'none';

  const infoBtn = document.getElementById('chat-info-btn');
  const groupSettingsBtn = document.getElementById('group-settings-btn');
  const modeBtn = document.getElementById('chat-mode-btn');
  if (infoBtn) infoBtn.style.display = window.currentGroupChat ? 'none' : 'block';
  if (groupSettingsBtn) groupSettingsBtn.style.display = window.currentGroupChat ? 'block' : 'none';
  if (modeBtn) modeBtn.style.display = 'block';

  const input = document.getElementById('chat-input');
  if (input) {
    input.style.display = 'block';
    input.value = '';
    input.placeholder = t('input_placeholder');
  }
  const toggleBtn = document.getElementById('toggle-voice-btn');
  if (toggleBtn) toggleBtn.textContent = '🎤';
  isVoiceMode = false;

  updateSendButtonVisibility();
  clearPendingQuote();
  closeChatPlusPanel();

  const messagesContainer = document.getElementById('chat-messages');
  messagesContainer.innerHTML = '';

  if (currentConversationId) {
    loadMessages(currentConversationId);
    startPolling();
  }
}

export function closeChatWindow() {
  currentConversationId = null;
  currentAgentId = null;
  currentAgentType = 'my';
  currentSenderAgentId = null;
  currentMode = 'free';
  lastMessageTime = null;
  lastMessageId = 0;
  currentOffset = 0;
  isLoadingMore = false;
  hasMoreMessages = true;

  stopPolling();

  document.getElementById('view-chat-window').style.display = 'none';
  document.querySelector('.bottom-nav').style.display = 'flex';
  document.querySelector('.top-bar').style.display = 'flex';
  const infoBtn = document.getElementById('chat-info-btn');
  if (infoBtn) infoBtn.style.display = 'none';
  const groupSettingsBtn = document.getElementById('group-settings-btn');
  if (groupSettingsBtn) groupSettingsBtn.style.display = 'none';
  const modeBtn = document.getElementById('chat-mode-btn');
  if (modeBtn) modeBtn.style.display = 'none';
  clearPendingQuote();
  closeChatPlusPanel();
}

function startPolling() {
  stopPolling();
  pollingTimer = setInterval(async () => {
    if (!currentConversationId) return;
    try {
      const data = await api.getConversationMessages(currentConversationId, 50, 0, lastMessageId);
      const newMessages = data.messages || [];
      if (newMessages.length > 0) {
        for (const msg of newMessages) {
          if (msg.id === lastMessageId) continue;
          appendMessage(msg.sender, msg.content, msg.sender_name, msg.id, msg.created_at);
          if (msg.id > lastMessageId) lastMessageId = msg.id;
        }
      }
    } catch (e) {
      console.warn('轮询新消息失败', e);
    }
  }, 5000);
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
}

function updateModeText() {
  const modeTextEl = document.getElementById('chat-mode-text');
  if (!modeTextEl) return;
  const modeMap = {
    'free': t('free_mode'),
    'domain': t('domain_mode'),
    'proposition': t('proposition_mode'),
    'normal': t('normal_chat'),
    'task': t('task_mode')
  };
  modeTextEl.textContent = modeMap[currentMode] || currentMode;
}

function openModeMenu() {
  const isGroup = window.currentGroupChat;
  const isOwner = window.currentGroupOwner || false;

  let menuItems = [];
  if (!isGroup) {
    menuItems = [
      { mode: 'free', label: t('free_mode') },
      { mode: 'domain', label: t('domain_mode') },
      { mode: 'proposition', label: t('proposition_mode') }
    ];
  } else {
    menuItems = [{ mode: 'normal', label: t('normal_chat') }];
    if (isOwner) {
      menuItems.push({ mode: 'task', label: t('task_mode') });
    }
  }

  const menu = document.getElementById('mode-menu');
  const content = document.getElementById('mode-menu-content');
  if (!menu || !content) return;

  let html = '';
  menuItems.forEach(item => {
    const active = item.mode === currentMode ? 'active-mode' : '';
    html += `
      <div class="plus-menu-item mode-item ${active}" data-mode="${item.mode}">
        <span class="plus-menu-label">${item.label}</span>
      </div>
    `;
  });
  content.innerHTML = html;
  menu.style.display = 'block';

  const modeBtn = document.getElementById('chat-mode-btn');
  if (modeBtn) {
    const rect = modeBtn.getBoundingClientRect();
    content.style.left = rect.left + 'px';
    content.style.top = (rect.bottom + 5) + 'px';
    content.style.position = 'fixed';
  }

  content.querySelectorAll('.mode-item').forEach(el => {
    el.addEventListener('click', () => {
      currentMode = el.dataset.mode;
      updateModeText();
      closeModeMenu();
    });
  });

  document.getElementById('mode-menu-overlay').onclick = closeModeMenu;
}

function closeModeMenu() {
  document.getElementById('mode-menu').style.display = 'none';
}

async function loadMessages(conversationId) {
  currentOffset = 0;
  hasMoreMessages = true;
  const container = document.getElementById('chat-messages');
  container.innerHTML = '';
  try {
    const data = await api.getConversationMessages(conversationId, PAGE_SIZE, 0);
    const messages = data.messages || [];
    if (messages.length < PAGE_SIZE) {
      hasMoreMessages = false;
    }
    messages.forEach(msg => {
      appendMessage(msg.sender, msg.content, msg.sender_name, msg.id, msg.created_at);
      if (msg.id > lastMessageId) lastMessageId = msg.id;
    });
    currentOffset = messages.length;
    container.scrollTop = container.scrollHeight;
  } catch (err) {
    appendMessage('assistant', `${t('load_failed')}: ${err.message}`, 'AI', null, new Date().toISOString());
  }
}

async function handleScroll() {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  if (container.scrollTop <= 30 && hasMoreMessages && !isLoadingMore && currentConversationId) {
    isLoadingMore = true;
    try {
      const data = await api.getConversationMessages(currentConversationId, PAGE_SIZE, currentOffset);
      const olderMessages = data.messages || [];
      if (olderMessages.length < PAGE_SIZE) {
        hasMoreMessages = false;
      }
      if (olderMessages.length > 0) {
        const prevScrollHeight = container.scrollHeight;
        for (let i = olderMessages.length - 1; i >= 0; i--) {
          const msg = olderMessages[i];
          const wrapper = createMessageElement(msg.sender, msg.content, msg.sender_name, msg.id, msg.created_at, false, true);
          container.insertBefore(wrapper, container.firstChild);
        }
        container.scrollTop = container.scrollHeight - prevScrollHeight;
      }
      currentOffset += olderMessages.length;
    } catch (e) {
      console.error(t('load_failed'), e);
    } finally {
      isLoadingMore = false;
    }
  }
}

function createMessageElement(role, content, senderName, messageId, timeIso, isPending = false, skipTimeTag = false) {
  const wrapper = document.createElement('div');
  wrapper.className = `message-row ${role}`;
  wrapper.dataset.messageId = messageId || '';
  wrapper.dataset.role = role;
  wrapper.dataset.senderName = senderName || (role === 'user' ? '我' : 'AI');
  wrapper.dataset.content = content;

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = (senderName || (role === 'user' ? '我' : 'AI')).charAt(0).toUpperCase();

  const bubble = document.createElement('div');
  bubble.className = `message ${role}`;
  if (role === 'user' && senderName && senderName !== '我') {
    bubble.innerHTML = `<span class="group-msg-sender">${senderName}:</span> ${content}`;
  } else {
    bubble.textContent = content;
  }

  if (role === 'user') {
    wrapper.appendChild(bubble);
    wrapper.appendChild(avatar);
    if (isPending) {
      const status = document.createElement('span');
      status.className = 'message-status pending';
      status.textContent = t('sending');
      wrapper.appendChild(status);
    }
  } else {
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
  }

  return wrapper;
}

function appendMessage(role, content, senderName = null, messageId = null, timeIso = null, isPending = false) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;

  if (timeIso) insertTimeTag(timeIso);

  const wrapper = createMessageElement(role, content, senderName, messageId, timeIso, isPending);
  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;

  if (role === 'assistant') {
    attachLongPress(wrapper);
  }
}

function insertTimeTag(timeIso) {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  if (!lastMessageTime) {
    lastMessageTime = timeIso;
    return;
  }
  const diff = new Date(timeIso) - new Date(lastMessageTime);
  if (Math.abs(diff) > 5 * 60 * 1000) {
    const tag = document.createElement('div');
    tag.className = 'time-tag';
    tag.textContent = formatTime(timeIso);
    container.appendChild(tag);
  }
  lastMessageTime = timeIso;
}

function formatTime(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  } else if (date.getFullYear() === now.getFullYear()) {
    return date.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' }) + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  } else {
    return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' }) + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  let text = input.value.trim();
  if (!text) return;

  const pendingQuote = getPendingQuote();
  if (pendingQuote) {
    text = `> ${t('quote')}：${pendingQuote}\n${text}`;
    clearPendingQuote();
  }

  const tempId = 'temp-' + Date.now();
  appendMessage('user', text, currentSenderAgentId ? '智能体' : '我', tempId, new Date().toISOString(), true);
  input.value = '';
  updateSendButtonVisibility();

  try {
    if (currentAgentType === 'friend' && currentAgentId) {
      try {
        await api.callAgent(currentAgentId, text);
      } catch (err) {
        updateMessageStatus(tempId, 'failed');
        return;
      }
    }

    const data = await api.sendMessage({
      conversation_id: currentConversationId,
      agent_id: currentAgentId,
      content: text,
      sender_agent_id: currentSenderAgentId
    });

    if (!currentConversationId) {
      currentConversationId = data.conversation_id;
    }
    updateMessageStatus(tempId, 'sent');
    appendMessage('assistant', data.assistant_reply, 'AI', null, new Date().toISOString());
  } catch (err) {
    updateMessageStatus(tempId, 'failed');
  }
}

function updateMessageStatus(messageId, status) {
  const wrapper = document.querySelector(`[data-message-id="${messageId}"]`);
  if (!wrapper) return;
  const existingStatus = wrapper.querySelector('.message-status');
  if (existingStatus) {
    if (status === 'sent') {
      existingStatus.remove();
    } else if (status === 'failed') {
      existingStatus.className = 'message-status failed';
      existingStatus.textContent = t('send_failed');
      const retryBtn = document.createElement('button');
      retryBtn.className = 'retry-btn';
      retryBtn.textContent = t('retry');
      retryBtn.addEventListener('click', () => {
        const content = wrapper.dataset.content;
        const input = document.getElementById('chat-input');
        input.value = content;
        updateSendButtonVisibility();
        sendMessage();
        wrapper.remove();
      });
      wrapper.appendChild(retryBtn);
    }
  } else if (status === 'failed') {
    const statusEl = document.createElement('span');
    statusEl.className = 'message-status failed';
    statusEl.textContent = t('send_failed');
    wrapper.appendChild(statusEl);
  }
}

// ==================== 聊天信息页 ====================
function openChatInfo() {
  const chatName = document.getElementById('chat-window-title').textContent;
  const contentHtml = `
    <div class="chat-info-header">
      <div class="chat-info-avatar">${chatName.charAt(0)}</div>
      <div class="chat-info-name">${chatName}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="switch-identity-entry">
        <span class="menu-label">${t('identity_switch')}</span>
        <span class="menu-value" id="current-identity-text">${t('self_identity')}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="set-remark-entry">
        <span class="menu-label">${t('set_remark')}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="complain-entry">
        <span class="menu-label">${t('complain')}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="delete-chat-entry">
        <span class="menu-label" style="color:#ff3b30;">${t('delete_chat')}</span>
      </div>
    </div>
  `;
  window.openSubpage(t('chat_info'), contentHtml, { showMore: false });

  setTimeout(() => {
    document.getElementById('switch-identity-entry').addEventListener('click', openIdentitySwitch);
    document.getElementById('set-remark-entry').addEventListener('click', () => {
      const remark = prompt(t('set_remark'), chatName);
      if (remark) alert(t('remark_saved'));
    });
    document.getElementById('complain-entry').addEventListener('click', () => alert(t('complain') + ' ' + t('coming_soon')));
    document.getElementById('delete-chat-entry').addEventListener('click', () => {
      if (confirm(t('delete_chat_confirm'))) alert(t('delete_success'));
    });
  }, 100);
}

async function openIdentitySwitch() {
  const contentHtml = `
    <div class="me-menu" id="identity-switch-list">
      <div class="me-menu-item identity-option" data-agent-id="">👤 ${t('self_identity')}</div>
      <div class="subpage-placeholder">${t('loading')}...</div>
    </div>
  `;
  window.openSubpage(t('identity_switch'), contentHtml);

  try {
    const data = await api.listMyAgents();
    const agents = data.agents || [];
    const container = document.getElementById('identity-switch-list');
    if (agents.length === 0) {
      container.innerHTML = `<div class="subpage-placeholder">${t('no_agents')}</div>`;
      return;
    }
    let html = `<div class="me-menu-item identity-option" data-agent-id="">👤 ${t('self_identity')}</div>`;
    agents.forEach(agent => {
      html += `
        <div class="me-menu-item identity-option" data-agent-id="${agent.agent_id}">
          <span class="menu-icon">🤖</span>
          ${agent.name}
        </div>
      `;
    });
    container.innerHTML = html;

    container.querySelectorAll('.identity-option').forEach(opt => {
      opt.addEventListener('click', () => {
        currentSenderAgentId = opt.dataset.agentId || null;
        window.closeSubpage();
        const baseTitle = document.getElementById('chat-window-title').textContent.split(' (')[0];
        document.getElementById('chat-window-title').textContent = currentSenderAgentId ? baseTitle + ' (智能体)' : baseTitle;
        openChatInfo();
      });
    });
  } catch (e) {
    document.getElementById('identity-switch-list').innerHTML = `<div class="subpage-placeholder">${t('load_failed')}: ${e.message}</div>`;
  }
}

// 暴露给 message_actions.js 使用
window.updateSendButtonVisibility = updateSendButtonVisibility;

document.addEventListener('click', (e) => {
  const menu = document.getElementById('message-context-menu');
  if (menu && !menu.contains(e.target)) {
    closeContextMenu();
  }
});