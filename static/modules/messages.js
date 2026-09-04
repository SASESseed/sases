// static/modules/messages.js
import { api } from './api.js';
import { openChatWindow } from './chat.js';
import { initPullToRefresh } from './utils.js';
import { t } from './i18n.js';

let initialized = false;

export async function initMessages() {
  const container = document.getElementById('messages-list');
  if (!container) return;
  if (initialized) return;
  initialized = true;
  await loadConversations(container);
}

async function loadConversations(container) {
  try {
    const data = await api.listConversations();
    const conversations = data.conversations || [];
    if (conversations.length === 0) {
      container.innerHTML = `<div class="empty">${t('no_conversations')}</div>`;
      return;
    }

    let html = '';
    conversations.forEach(conv => {
      const agentName = conv.title || '会话';
      const lastMessage = conv.last_message || '';
      const unread = conv.unread_count || 0;
      const pinned = conv.is_pinned ? 'pinned' : '';
      const lastSenderName = conv.last_sender_name || '';
      const displayLast = lastSenderName ? `${lastSenderName}: ${lastMessage}` : lastMessage;

      html += `
        <div class="session-item ${pinned}" data-conversation-id="${conv.id}" data-agent-id="${conv.agent_id || ''}" data-title="${agentName}">
          <div class="session-avatar">
            ${agentName.charAt(0)}
            ${unread > 0 ? `<span class="unread-badge">${unread}</span>` : ''}
          </div>
          <div class="session-info">
            <div class="session-name">${agentName}</div>
            <div class="session-last">${displayLast}</div>
          </div>
          <button class="session-more-btn" data-conversation-id="${conv.id}" data-pinned="${conv.is_pinned}">⋯</button>
        </div>
      `;
    });
    container.innerHTML = html;

    // 初始化下拉刷新
    initPullToRefresh(container, async () => {
      await loadConversations(container);
    });

    container.querySelectorAll('.session-item').forEach(item => {
      item.addEventListener('click', (e) => {
        if (e.target.closest('.session-more-btn')) return;
        const conversationId = item.dataset.conversationId;
        const agentId = item.dataset.agentId || null;
        const title = item.dataset.title;
        openChatWindow(conversationId, title, agentId);
      });
    });

    container.querySelectorAll('.session-more-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const convId = btn.dataset.conversationId;
        const pinned = btn.dataset.pinned === '1' ? true : false;
        showSessionActions(convId, pinned);
      });
    });
  } catch (e) {
    container.innerHTML = `<div class="empty">${t('load_failed')}: ${e.message}</div>`;
  }
}

function showSessionActions(conversationId, pinned) {
  const action = prompt(
    `${t('choose_action')}\n1. ${pinned ? t('unpin') : t('pin')}\n2. ${t('mark_read')}\n3. ${t('delete_conversation')}\n0. ${t('cancel')}`
  );
  if (action === '1') {
    togglePin(conversationId, !pinned);
  } else if (action === '2') {
    markRead(conversationId);
  } else if (action === '3') {
    deleteConversation(conversationId);
  }
}

async function togglePin(conversationId, pinned) {
  try {
    await api.togglePinConversation(conversationId, pinned);
    location.reload();
  } catch (e) {
    alert(t('operation_failed') + ': ' + e.message);
  }
}

async function markRead(conversationId) {
  try {
    await api.markConversationRead(conversationId);
    location.reload();
  } catch (e) {
    alert(t('operation_failed') + ': ' + e.message);
  }
}

async function deleteConversation(conversationId) {
  if (!confirm(t('delete_confirm'))) return;
  try {
    await api.deleteConversation(conversationId);
    location.reload();
  } catch (e) {
    alert(t('delete_failed') + ': ' + e.message);
  }
}