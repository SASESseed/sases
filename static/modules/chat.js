// static/modules/chat.js
import { api } from './api.js';
import { closeGroupChat, sendGroupMessage } from './group_chat.js';

let chatInitialized = false;
let currentConversationId = null;
let currentAgentId = null;
let currentAgentType = 'my';
let currentSenderAgentId = null;
let currentMode = 'free';
let isVoiceMode = false;
let pendingQuote = null;
let lastMessageTime = null;

// 分页状态
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
    input.placeholder = '按住说话（模拟）';
  } else {
    input.style.display = 'block';
    toggleBtn.textContent = '🎤';
    input.placeholder = '输入消息...';
  }
}

export function openChatWindow(conversationId, chatName, agentId = null, agentType = 'my') {
  currentConversationId = conversationId ? parseInt(conversationId) : null;
  currentAgentId = agentId;
  currentAgentType = agentType;
  currentSenderAgentId = null;
  currentMode = 'free';
  pendingQuote = null;
  lastMessageTime = null;
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
  }
  const toggleBtn = document.getElementById('toggle-voice-btn');
  if (toggleBtn) toggleBtn.textContent = '🎤';
  isVoiceMode = false;

  updateSendButtonVisibility();
  hideQuoteBar();
  closeChatPlusPanel();

  const messagesContainer = document.getElementById('chat-messages');
  messagesContainer.innerHTML = '';

  if (currentConversationId) {
    loadMessages(currentConversationId);
  }
}

export function closeChatWindow() {
  currentConversationId = null;
  currentAgentId = null;
  currentAgentType = 'my';
  currentSenderAgentId = null;
  currentMode = 'free';
  pendingQuote = null;
  lastMessageTime = null;
  currentOffset = 0;
  isLoadingMore = false;
  hasMoreMessages = true;

  document.getElementById('view-chat-window').style.display = 'none';
  document.querySelector('.bottom-nav').style.display = 'flex';
  document.querySelector('.top-bar').style.display = 'flex';
  const infoBtn = document.getElementById('chat-info-btn');
  if (infoBtn) infoBtn.style.display = 'none';
  const groupSettingsBtn = document.getElementById('group-settings-btn');
  if (groupSettingsBtn) groupSettingsBtn.style.display = 'none';
  const modeBtn = document.getElementById('chat-mode-btn');
  if (modeBtn) modeBtn.style.display = 'none';
  hideQuoteBar();
  closeChatPlusPanel();
}

function updateModeText() {
  const modeTextEl = document.getElementById('chat-mode-text');
  if (!modeTextEl) return;
  const modeMap = {
    'free': '自由模式',
    'domain': '领域模式',
    'proposition': '命题模式',
    'normal': '普通聊天',
    'task': '任务模式'
  };
  modeTextEl.textContent = modeMap[currentMode] || currentMode;
}

function openModeMenu() {
  const isGroup = window.currentGroupChat;
  const isOwner = window.currentGroupOwner || false;

  let menuItems = [];
  if (!isGroup) {
    menuItems = [
      { mode: 'free', label: '自由模式' },
      { mode: 'domain', label: '领域模式' },
      { mode: 'proposition', label: '命题模式' }
    ];
  } else {
    menuItems = [{ mode: 'normal', label: '普通聊天' }];
    if (isOwner) {
      menuItems.push({ mode: 'task', label: '任务模式' });
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
    });
    currentOffset = messages.length;
    container.scrollTop = container.scrollHeight;
  } catch (err) {
    appendMessage('assistant', `加载历史消息失败：${err.message}`, 'AI', null, new Date().toISOString());
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
        // 在顶部插入更早的消息，不触发时间标签，避免混乱
        for (let i = olderMessages.length - 1; i >= 0; i--) {
          const msg = olderMessages[i];
          const wrapper = createMessageElement(msg.sender, msg.content, msg.sender_name, msg.id, msg.created_at, false, true);
          container.insertBefore(wrapper, container.firstChild);
        }
        container.scrollTop = container.scrollHeight - prevScrollHeight;
      }
      currentOffset += olderMessages.length;
    } catch (e) {
      console.error('加载更多消息失败', e);
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
      status.textContent = '发送中...';
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

  if (pendingQuote) {
    text = `> 引用：${pendingQuote}\n${text}`;
    pendingQuote = null;
    hideQuoteBar();
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
      existingStatus.textContent = '发送失败';
      const retryBtn = document.createElement('button');
      retryBtn.className = 'retry-btn';
      retryBtn.textContent = '重试';
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
    statusEl.textContent = '发送失败';
    wrapper.appendChild(statusEl);
  }
}

// ==================== 长按菜单 ====================
function createContextMenu() {
  const oldMenu = document.getElementById('message-context-menu');
  if (oldMenu) oldMenu.remove();

  const menu = document.createElement('div');
  menu.id = 'message-context-menu';
  menu.className = 'message-context-menu';
  menu.style.display = 'none';
  document.body.appendChild(menu);
}

function showContextMenu(x, y, wrapper) {
  const menu = document.getElementById('message-context-menu');
  if (!menu) return;
  menu.innerHTML = `
    <div class="context-menu-item" data-action="quote">引用</div>
    <div class="context-menu-item" data-action="reply">帮我回复</div>
  `;
  menu.style.display = 'block';
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';

  menu.querySelector('[data-action="quote"]').addEventListener('click', () => {
    pendingQuote = wrapper.dataset.content;
    showQuoteBar(pendingQuote);
    closeContextMenu();
  });

  menu.querySelector('[data-action="reply"]').addEventListener('click', async () => {
    const content = wrapper.dataset.content;
    try {
      const data = await api.suggestReply(content);
      const reply = data.response || '（无建议）';
      const input = document.getElementById('chat-input');
      if (input) {
        input.value = reply;
        updateSendButtonVisibility();
        input.focus();
      }
    } catch (e) {
      alert('生成回复失败：' + e.message);
    }
    closeContextMenu();
  });
}

function closeContextMenu() {
  const menu = document.getElementById('message-context-menu');
  if (menu) menu.style.display = 'none';
}

function attachLongPress(wrapper) {
  let timer = null;
  wrapper.addEventListener('touchstart', (e) => {
    const touch = e.touches[0];
    timer = setTimeout(() => {
      showContextMenu(touch.clientX, touch.clientY, wrapper);
    }, 800);
  }, { passive: true });

  wrapper.addEventListener('touchend', () => {
    if (timer) clearTimeout(timer);
  });
  wrapper.addEventListener('touchmove', () => {
    if (timer) clearTimeout(timer);
  });
}

// ==================== 引用条 ====================
function showQuoteBar(text) {
  let bar = document.getElementById('quote-bar');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'quote-bar';
    bar.className = 'quote-bar';
    bar.innerHTML = `
      <span class="quote-text"></span>
      <button class="quote-close">×</button>
    `;
    const inputArea = document.querySelector('.chat-input-area');
    inputArea.parentElement.insertBefore(bar, inputArea);
    bar.querySelector('.quote-close').addEventListener('click', () => {
      pendingQuote = null;
      hideQuoteBar();
    });
  }
  bar.querySelector('.quote-text').textContent = text;
  bar.style.display = 'flex';
}

function hideQuoteBar() {
  const bar = document.getElementById('quote-bar');
  if (bar) bar.style.display = 'none';
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
        <span class="menu-label">切换身份</span>
        <span class="menu-value" id="current-identity-text">以本人身份</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="set-remark-entry">
        <span class="menu-label">设置备注和标签</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="complain-entry">
        <span class="menu-label">投诉</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="delete-chat-entry">
        <span class="menu-label" style="color:#ff3b30;">删除聊天</span>
      </div>
    </div>
  `;
  window.openSubpage('聊天信息', contentHtml, { showMore: false });

  setTimeout(() => {
    document.getElementById('switch-identity-entry').addEventListener('click', openIdentitySwitch);
    document.getElementById('set-remark-entry').addEventListener('click', () => {
      const remark = prompt('请输入备注名：', chatName);
      if (remark) alert('备注已设置（模拟）');
    });
    document.getElementById('complain-entry').addEventListener('click', () => alert('投诉功能待实现'));
    document.getElementById('delete-chat-entry').addEventListener('click', () => {
      if (confirm('确定删除聊天记录吗？')) alert('已删除（模拟）');
    });
  }, 100);
}

async function openIdentitySwitch() {
  const contentHtml = `
    <div class="me-menu" id="identity-switch-list">
      <div class="me-menu-item identity-option" data-agent-id="">👤 以本人身份</div>
      <div class="subpage-placeholder">加载智能体...</div>
    </div>
  `;
  window.openSubpage('切换身份', contentHtml);

  try {
    const data = await api.listMyAgents();
    const agents = data.agents || [];
    const container = document.getElementById('identity-switch-list');
    if (agents.length === 0) {
      container.innerHTML = '<div class="subpage-placeholder">暂无智能体</div>';
      return;
    }
    let html = '<div class="me-menu-item identity-option" data-agent-id="">👤 以本人身份</div>';
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
    document.getElementById('identity-switch-list').innerHTML = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }
}

// ==================== 聊天加号面板 ====================
function toggleChatPlusPanel() {
  const panel = document.getElementById('chat-plus-panel');
  if (!panel) return;
  if (panel.style.display === 'block') {
    closeChatPlusPanel();
  } else {
    openChatPlusPanel();
  }
}

function openChatPlusPanel() {
  const panel = document.getElementById('chat-plus-panel');
  if (!panel) return;
  const content = document.getElementById('chat-plus-content');
  if (content) {
    const items = [
      { icon: '📷', label: '相册', action: () => alert('相册功能待实现') },
      { icon: '💰', label: '转账', action: () => alert('转账功能待实现') },
      { icon: '🧧', label: '红包', action: () => alert('红包功能待实现') },
      { icon: '📁', label: '文件', action: () => alert('文件功能待实现') },
      { icon: '📍', label: '位置', action: () => alert('位置功能待实现') }
    ];
    let html = '<div class="chat-plus-grid">';
    items.forEach(item => {
      html += `
        <div class="chat-plus-item">
          <div class="chat-plus-icon">${item.icon}</div>
          <div class="chat-plus-label">${item.label}</div>
        </div>
      `;
    });
    html += '</div>';
    content.innerHTML = html;
    content.querySelectorAll('.chat-plus-item').forEach((el, index) => {
      el.addEventListener('click', () => {
        closeChatPlusPanel();
        items[index].action();
      });
    });
  }
  panel.style.display = 'block';
}

function closeChatPlusPanel() {
  const panel = document.getElementById('chat-plus-panel');
  if (panel) panel.style.display = 'none';
}

document.addEventListener('click', (e) => {
  const menu = document.getElementById('message-context-menu');
  if (menu && !menu.contains(e.target)) {
    closeContextMenu();
  }
});