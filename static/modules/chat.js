// static/modules/chat.js
import { api } from './api.js';
import { closeGroupChat, sendGroupMessage } from './group_chat.js';
import { appendMessage, createMessageElement, updateMessageStatus } from './chat_ui.js';
import { showWorkWarning, sendWorkCommand, sendCommanderTask, showFreeModeGuide } from './chat_work.js';
import { updateIdentityButton, openIdentitySwitch } from './chat_identity.js';
import { createContextMenu, showQuoteBar, hideQuoteBar, openChatInfo, toggleChatPlusPanel, closeChatPlusPanel } from './chat_menu.js';

export const chatState = {
  initialized: false,
  conversationId: null,
  agentId: null,
  agentType: 'my',
  senderAgentId: null,
  mode: 'free',
  voiceMode: false,
  pendingQuote: null,
  lastMessageTime: null,
  offset: 0,
  loadingMore: false,
  hasMore: true
};

const PAGE_SIZE = 50;

function handleSend() {
  if (window.currentGroupChat) {
    sendGroupMessage();
    return;
  }

  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  if (chatState.mode === 'free') {
    // 支持全角：和半角:
    const execMatch = text.match(/^执行[：:]\s*(.+)$/);
    if (execMatch) {
      const command = execMatch[1].trim();
      if (!localStorage.getItem('sases_disable_work_warning')) {
        showWorkWarning(command, chatState, api);
        return;
      }
      sendWorkCommand(command, chatState, api);
      return;
    }

    const taskMatch = text.match(/^任务[：:]\s*(.+)$/);
    if (taskMatch) {
      const taskText = taskMatch[1].trim();
      sendCommanderTask(taskText, chatState, api);
      return;
    }
  }

  sendMessage();
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  let text = input.value.trim();
  if (!text) return;

  if (chatState.pendingQuote) {
    text = `> 引用：${chatState.pendingQuote}\n${text}`;
    chatState.pendingQuote = null;
    hideQuoteBar();
  }

  const tempId = 'temp-' + Date.now();
  appendMessage('user', text, chatState.senderAgentId ? '智能体' : '我', tempId, new Date().toISOString(), true, chatState);
  input.value = '';
  updateSendButtonVisibility();

  try {
    if (chatState.agentType === 'friend' && chatState.agentId) {
      try {
        await api.callAgent(chatState.agentId, text);
      } catch (err) {
        updateMessageStatus(tempId, 'failed');
        return;
      }
    }

    const data = await api.sendMessage({
      conversation_id: chatState.conversationId,
      agent_id: chatState.agentId,
      content: text,
      sender_agent_id: chatState.senderAgentId,
      mode: chatState.mode
    });

    if (!chatState.conversationId) {
      chatState.conversationId = data.conversation_id;
    }
    updateMessageStatus(tempId, 'sent');
    appendMessage('assistant', data.assistant_reply, 'AI', null, new Date().toISOString(), false, chatState);

    // 上报新手引导动作：发送第一条消息（Day 1）
    if (typeof window.onboarding?.report === 'function') {
      window.onboarding.report('send_message');
    }
  } catch (err) {
    updateMessageStatus(tempId, 'failed');
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

window.updateSendButtonVisibility = updateSendButtonVisibility;
window.sendMessage = sendMessage;

function toggleVoiceMode() {
  const input = document.getElementById('chat-input');
  const toggleBtn = document.getElementById('toggle-voice-btn');
  if (!input || !toggleBtn) return;

  chatState.voiceMode = !chatState.voiceMode;
  if (chatState.voiceMode) {
    input.style.display = 'none';
    toggleBtn.textContent = '⌨️';
    input.placeholder = '按住说话（模拟）';
  } else {
    input.style.display = 'block';
    toggleBtn.textContent = '🎤';
    updateInputPlaceholder();
  }
}

function updateInputPlaceholder() {
  const input = document.getElementById('chat-input');
  if (!input) return;
  if (chatState.mode === 'normal') {
    input.placeholder = '输入消息...';
  } else if (chatState.mode === 'free') {
    input.placeholder = '聊天、执行：命令 或 任务：描述';
  } else {
    input.placeholder = '输入消息...';
  }
}

export function openChatWindow(conversationId, chatName, agentId = null, agentType = 'my') {
  chatState.conversationId = conversationId ? parseInt(conversationId) : null;
  chatState.agentId = agentId;
  chatState.agentType = agentType;
  chatState.senderAgentId = null;
  chatState.mode = 'free';
  chatState.pendingQuote = null;
  chatState.lastMessageTime = null;
  chatState.offset = 0;
  chatState.loadingMore = false;
  chatState.hasMore = true;

  updateModeText();
  updateInputPlaceholder();
  updateIdentityButton(chatState);

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
  if (modeBtn) {
    modeBtn.style.display = 'block';
    modeBtn.onclick = openModeMenu;
  }

  const input = document.getElementById('chat-input');
  if (input) {
    input.style.display = 'block';
    input.value = '';
  }
  const toggleBtn = document.getElementById('toggle-voice-btn');
  if (toggleBtn) toggleBtn.textContent = '🎤';
  chatState.voiceMode = false;

  updateSendButtonVisibility();
  hideQuoteBar();
  closeChatPlusPanel();

  const messagesContainer = document.getElementById('chat-messages');
  if (messagesContainer) {
    messagesContainer.innerHTML = '';
    if (!localStorage.getItem('sases_free_mode_guide_dismissed')) {
      showFreeModeGuide(messagesContainer);
    }
  }

  if (chatState.conversationId) {
    loadMessages(chatState.conversationId);
  }
}

export function closeChatWindow() {
  chatState.conversationId = null;
  chatState.agentId = null;
  chatState.agentType = 'my';
  chatState.senderAgentId = null;
  chatState.mode = 'free';
  chatState.pendingQuote = null;
  chatState.lastMessageTime = null;
  chatState.offset = 0;
  chatState.loadingMore = false;
  chatState.hasMore = true;

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
    'normal': '普通模式'
  };
  modeTextEl.textContent = modeMap[chatState.mode] || chatState.mode;
}

function openModeMenu() {
  const menu = document.getElementById('mode-menu');
  const content = document.getElementById('mode-menu-content');
  if (!menu || !content) return;

  content.innerHTML = `
    <div class="plus-menu-item mode-item ${chatState.mode === 'normal' ? 'active-mode' : ''}" data-mode="normal">
      <span class="plus-menu-label">普通模式</span>
      <span class="plus-menu-desc" style="font-size:12px;color:#888;">纯聊天，不触发任何功能</span>
    </div>
    <div class="plus-menu-item mode-item ${chatState.mode === 'free' ? 'active-mode' : ''}" data-mode="free">
      <span class="plus-menu-label">自由模式</span>
      <span class="plus-menu-desc" style="font-size:12px;color:#888;">可执行指令、任务协作、分析图片</span>
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
  document.getElementById('mode-menu-overlay').onclick = closeModeMenu;

  content.querySelectorAll('.mode-item').forEach(el => {
    el.addEventListener('click', () => {
      chatState.mode = el.dataset.mode;
      updateModeText();
      updateInputPlaceholder();
      closeModeMenu();
    });
  });
}

function closeModeMenu() {
  document.getElementById('mode-menu').style.display = 'none';
}

async function loadMessages(conversationId) {
  chatState.offset = 0;
  chatState.hasMore = true;
  const container = document.getElementById('chat-messages');
  if (!container) return;
  container.innerHTML = '';
  try {
    const data = await api.getConversationMessages(conversationId, PAGE_SIZE, 0);
    const messages = data.messages || [];
    if (messages.length < PAGE_SIZE) {
      chatState.hasMore = false;
    }
    messages.forEach(msg => {
      appendMessage(msg.sender, msg.content, msg.sender_name, msg.id, msg.created_at, false, chatState);
    });
    chatState.offset = messages.length;
    container.scrollTop = container.scrollHeight;
  } catch (err) {
    appendMessage('assistant', `加载历史消息失败：${err.message}`, 'AI', null, new Date().toISOString(), false, chatState);
  }
}

async function handleScroll() {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  if (container.scrollTop <= 30 && chatState.hasMore && !chatState.loadingMore && chatState.conversationId) {
    chatState.loadingMore = true;
    try {
      const data = await api.getConversationMessages(chatState.conversationId, PAGE_SIZE, chatState.offset);
      const olderMessages = data.messages || [];
      if (olderMessages.length < PAGE_SIZE) {
        chatState.hasMore = false;
      }
      if (olderMessages.length > 0) {
        const prevScrollHeight = container.scrollHeight;
        for (let i = olderMessages.length - 1; i >= 0; i--) {
          const msg = olderMessages[i];
          const wrapper = createMessageElement(msg.sender, msg.content, msg.sender_name, msg.id, msg.created_at, false, true, chatState);
          container.insertBefore(wrapper, container.firstChild);
        }
        container.scrollTop = container.scrollHeight - prevScrollHeight;
      }
      chatState.offset += olderMessages.length;
    } catch (e) {
      console.error('加载更多消息失败', e);
    } finally {
      chatState.loadingMore = false;
    }
  }
}

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

  if (!sendBtn || !input || !backBtn || !infoBtn || !modeBtn || chatState.initialized) return;
  chatState.initialized = true;

  sendBtn.addEventListener('click', handleSend);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });
  input.addEventListener('input', updateSendButtonVisibility);

  backBtn.addEventListener('click', handleBack);
  infoBtn.addEventListener('click', () => openChatInfo(chatState));
  toggleVoiceBtn.addEventListener('click', toggleVoiceMode);
  identityBtn.addEventListener('click', () => openIdentitySwitch(chatState, api));
  inputPlusBtn.addEventListener('click', toggleChatPlusPanel);

  if (messagesContainer) {
    messagesContainer.addEventListener('scroll', handleScroll);
  }

  updateSendButtonVisibility();
  updateIdentityButton(chatState);
  createContextMenu();
}