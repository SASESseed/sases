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

window.chatState = chatState;
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
    const execMatch = text.match(/^(?:执行|#1)[：:]\s*(.+)$/);
    if (execMatch) {
      const command = execMatch[1].trim();
      if (!localStorage.getItem('sases_disable_work_warning')) {
        showWorkWarning(command, chatState, api);
        return;
      }
      sendWorkCommand(command, chatState, api);
      return;
    }

    const taskMatch = text.match(/^(?:任务|#2)[：:]\s*(.+)$/);
    if (taskMatch) {
      const taskText = taskMatch[1].trim();
      sendCommanderTask(taskText, chatState, api);
      return;
    }
  }

  sendMessage();
}

async function sendTransfer(receiver_id, amount, message, conversation_id) {
  try {
    const res = await api.transferCredits(receiver_id, amount, message, conversation_id);
    return res;
  } catch (e) {
    console.error('[TRANSFER] sendTransfer failed', e);
    throw e;
  }
}


async function sendMessage() {
  const input = document.getElementById('chat-input');

  // 若有待发送附件，先上传再拼接
  if (chatState.pendingAttachment) {
    const att = chatState.pendingAttachment;
    try {
      let _url = '';
      if (att.type === 'image') {
        const res = await api.uploadImage(att.file);
        _url = res && res.url ? res.url : '';
        if (_url) input.value = '[IMAGE]:' + _url + (input.value ? ' ' + input.value : '');
      } else {
        const res = await api.uploadFile(att.file);
        _url = res && res.url ? res.url : '';
        if (_url) input.value = '[FILE]:' + _url + '|' + att.name + '|' + att.size + (input.value ? ' ' + input.value : '');
      }
    } catch (e) {
      alert('上传失败: ' + (e.message || ''));
      return;
    }
    chatState.pendingAttachment = null;
    if (typeof window.__sasesClearAttachment === 'function') window.__sasesClearAttachment();
  }

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
    if (data.assistant_reply) {
      appendMessage('assistant', data.assistant_reply, 'AI', null, new Date().toISOString(), false, chatState);
    }

    if (data.proposed_run_id) {
      showProposedRunCard(data.proposed_run_id);
    }

    // ========== 草稿模式：渲染可编辑任务编辑器 ==========
    if (data.swarm && data.swarm_status === 'draft' && data.task_id) {
      const steps = data.steps || [];
      showTaskDraftEditor(data.task_id, steps);
    }
    // ========== 普通蜂群任务：显示操作按钮 ==========
    else if (data.swarm && data.task_id) {
      showSwarmActionButtons(data.task_id, text, data.swarm_status);
    }

    if (typeof window.onboarding?.report === 'function') {
      window.onboarding.report('send_message');
    }
  } catch (err) {
    updateMessageStatus(tempId, 'failed');
  }
}

// ========== 草稿任务编辑器 ==========
function showProposedRunCard(runId) {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  const wrap = document.createElement('div');
  wrap.style.margin = '8px 12px';
  wrap.style.padding = '12px';
  wrap.style.background = '#fff9e6';
  wrap.style.border = '1px solid #ffcc00';
  wrap.style.borderRadius = '8px';
  wrap.id = 'proposed-run-' + runId;
  const title = document.createElement('div');
  title.textContent = '⚡ 调度员提议执行此任务';
  title.style.fontWeight = '600';
  title.style.marginBottom = '8px';
  wrap.appendChild(title);
  const btnGroup = document.createElement('div');
  btnGroup.style.display = 'flex';
  btnGroup.style.gap = '8px';
  btnGroup.style.justifyContent = 'flex-end';
  const rejectBtn = document.createElement('button');
  rejectBtn.textContent = '✕ 取消';
  rejectBtn.style.padding = '6px 16px';
  rejectBtn.style.fontSize = '13px';
  rejectBtn.style.border = '1px solid #ccc';
  rejectBtn.style.background = '#fff';
  rejectBtn.style.borderRadius = '4px';
  rejectBtn.style.cursor = 'pointer';
  rejectBtn.onclick = async () => {
    try {
      await api.rejectRun(runId);
      wrap.remove();
    } catch (e) {
      alert('取消失败：' + (e.message || '未知错误'));
    }
  };
  const confirmBtn = document.createElement('button');
  confirmBtn.textContent = '▶ 执行';
  confirmBtn.style.padding = '6px 16px';
  confirmBtn.style.fontSize = '13px';
  confirmBtn.style.border = 'none';
  confirmBtn.style.color = '#fff';
  confirmBtn.style.background = '#007aff';
  confirmBtn.style.borderRadius = '4px';
  confirmBtn.style.cursor = 'pointer';
  confirmBtn.onclick = async () => {
    confirmBtn.disabled = true;
    confirmBtn.textContent = '已提交';
    try {
      await api.confirmRun(runId);
      wrap.remove();
    } catch (e) {
      confirmBtn.disabled = false;
      confirmBtn.textContent = '▶ 执行';
      alert('确认失败：' + (e.message || '未知错误'));
    }
  };
  btnGroup.appendChild(rejectBtn);
  btnGroup.appendChild(confirmBtn);
  wrap.appendChild(btnGroup);
  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;
}



function showTaskDraftEditor(taskId, steps) {
  const container = document.getElementById('chat-messages');
  if (!container) return;

  const wrap = document.createElement('div');
  wrap.style.margin = '8px 12px';
  wrap.style.padding = '12px';
  wrap.style.background = '#f8f9fa';
  wrap.style.borderRadius = '8px';
  wrap.style.border = '1px solid #e0e0e0';
  wrap.id = `task-draft-${taskId}`;

  const title = document.createElement('div');
  title.textContent = '📝 任务草稿（可编辑）';
  title.style.fontWeight = '600';
  title.style.marginBottom = '10px';
  title.style.fontSize = '14px';
  wrap.appendChild(title);

  const list = document.createElement('div');
  list.style.display = 'flex';
  list.style.flexDirection = 'column';
  list.style.gap = '8px';
  list.style.marginBottom = '10px';

  let currentSteps = steps.map(s => ({
    step: s.step,
    description: s.description || '',
    command: s.command || ''
  }));

  function renderList() {
    list.innerHTML = '';
    currentSteps.forEach((s, idx) => {
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.flexDirection = 'column';
      row.style.gap = '4px';
      row.style.padding = '6px';
      row.style.background = '#fff';
      row.style.borderRadius = '4px';
      row.style.border = '1px solid #ddd';

      const topLine = document.createElement('div');
      topLine.style.display = 'flex';
      topLine.style.alignItems = 'center';
      topLine.style.gap = '6px';

      const numLabel = document.createElement('span');
      numLabel.textContent = `步骤 ${idx + 1}`;
      numLabel.style.fontSize = '12px';
      numLabel.style.color = '#666';
      numLabel.style.minWidth = '50px';
      topLine.appendChild(numLabel);

      const delBtn = document.createElement('button');
      delBtn.textContent = '✕ 删除';
      delBtn.style.marginLeft = 'auto';
      delBtn.style.fontSize = '12px';
      delBtn.style.border = '1px solid #ff3b30';
      delBtn.style.color = '#ff3b30';
      delBtn.style.background = '#fff';
      delBtn.style.borderRadius = '4px';
      delBtn.style.padding = '2px 8px';
      delBtn.style.cursor = 'pointer';
      delBtn.onclick = () => {
        currentSteps.splice(idx, 1);
        renderList();
      };
      topLine.appendChild(delBtn);
      row.appendChild(topLine);

      const descInput = document.createElement('input');
      descInput.type = 'text';
      descInput.value = s.description || '';
      descInput.placeholder = '描述';
      descInput.style.fontSize = '12px';
      descInput.style.padding = '4px 8px';
      descInput.style.border = '1px solid #ddd';
      descInput.style.borderRadius = '4px';
      descInput.style.outline = 'none';
      descInput.oninput = (e) => { currentSteps[idx].description = e.target.value; };
      row.appendChild(descInput);

      const cmdInput = document.createElement('input');
      cmdInput.type = 'text';
      cmdInput.value = s.command || '';
      cmdInput.placeholder = '命令';
      cmdInput.style.fontSize = '13px';
      cmdInput.style.padding = '4px 8px';
      cmdInput.style.border = '1px solid #ddd';
      cmdInput.style.borderRadius = '4px';
      cmdInput.style.fontFamily = 'Consolas, Monaco, monospace';
      cmdInput.style.outline = 'none';
      cmdInput.oninput = (e) => { currentSteps[idx].command = e.target.value; };
      row.appendChild(cmdInput);

      list.appendChild(row);
    });
  }

  renderList();
  wrap.appendChild(list);

  const addBtn = document.createElement('button');
  addBtn.textContent = '+ 添加步骤';
  addBtn.style.fontSize = '12px';
  addBtn.style.padding = '4px 12px';
  addBtn.style.border = '1px dashed #999';
  addBtn.style.color = '#666';
  addBtn.style.background = '#fff';
  addBtn.style.borderRadius = '4px';
  addBtn.style.cursor = 'pointer';
  addBtn.style.marginBottom = '12px';
  addBtn.onclick = () => {
    currentSteps.push({ step: currentSteps.length + 1, description: '', command: '' });
    renderList();
  };
  wrap.appendChild(addBtn);

  const btnGroup = document.createElement('div');
  btnGroup.style.display = 'flex';
  btnGroup.style.gap = '8px';
  btnGroup.style.justifyContent = 'flex-end';

  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = '取消';
  cancelBtn.style.padding = '6px 16px';
  cancelBtn.style.fontSize = '13px';
  cancelBtn.style.border = '1px solid #ccc';
  cancelBtn.style.background = '#fff';
  cancelBtn.style.borderRadius = '4px';
  cancelBtn.style.cursor = 'pointer';
  cancelBtn.onclick = async () => {
    cancelBtn.disabled = true;
    try {
      const token = localStorage.getItem('sases_token');
      await fetch('/swarm/cancel', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ task_id: taskId })
      });
    } catch (e) {
      console.error('取消失败', e);
    }
    wrap.remove();
  };
  btnGroup.appendChild(cancelBtn);

  const confirmBtn = document.createElement('button');
  confirmBtn.textContent = '✓ 确认执行';
  confirmBtn.style.padding = '6px 16px';
  confirmBtn.style.fontSize = '13px';
  confirmBtn.style.border = 'none';
  confirmBtn.style.color = '#fff';
  confirmBtn.style.background = '#007aff';
  confirmBtn.style.borderRadius = '4px';
  confirmBtn.style.cursor = 'pointer';
  confirmBtn.onclick = async () => {
    confirmBtn.disabled = true;
    confirmBtn.textContent = '已提交';
    try {
      const token = localStorage.getItem('sases_token');
      const resp = await fetch('/swarm/confirm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ task_id: taskId, edited_steps: currentSteps })
      });
      const data = await resp.json();
      if (data.status === 'confirmed') {
        wrap.remove();
      } else {
        confirmBtn.disabled = false;
        confirmBtn.textContent = '✓ 确认执行';
        alert('确认失败：' + (data.message || '未知错误'));
      }
    } catch (e) {
      confirmBtn.disabled = false;
      confirmBtn.textContent = '✓ 确认执行';
      alert('请求失败：' + e.message);
    }
  };
  btnGroup.appendChild(confirmBtn);

  wrap.appendChild(btnGroup);

  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;
}

// ========== 蜂群任务操作按钮（取消 + 误判反馈） ==========
function showSwarmActionButtons(taskId, originalInput, swarmStatus) {
  const container = document.getElementById('chat-messages');
  if (!container) return;

  const wrap = document.createElement('div');
  wrap.style.display = 'flex';
  wrap.style.justifyContent = 'center';
  wrap.style.gap = '10px';
  wrap.style.margin = '6px 12px';
  wrap.id = `swarm-actions-${taskId}`;

  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = '⏹ 取消执行';
  cancelBtn.style.padding = '6px 16px';
  cancelBtn.style.fontSize = '13px';
  cancelBtn.style.border = '1px solid #ff3b30';
  cancelBtn.style.color = '#ff3b30';
  cancelBtn.style.background = '#fff';
  cancelBtn.style.borderRadius = '16px';
  cancelBtn.style.cursor = 'pointer';
  cancelBtn.style.transition = 'all 0.2s';
  cancelBtn.onmouseenter = () => { cancelBtn.style.background = '#fff5f5'; };
  cancelBtn.onmouseleave = () => { cancelBtn.style.background = '#fff'; };

  cancelBtn.onclick = async () => {
    cancelBtn.disabled = true;
    cancelBtn.textContent = '已取消';
    cancelBtn.style.color = '#999';
    cancelBtn.style.borderColor = '#999';
    cancelBtn.style.cursor = 'default';
    try {
      const token = localStorage.getItem('sases_token');
      await fetch('/swarm/cancel', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ task_id: taskId })
      });
    } catch (e) {
      console.error('取消失败', e);
    }
    setTimeout(() => {
      if (wrap.parentNode) wrap.remove();
    }, 1500);
  };

  const feedbackBtn = document.createElement('button');
  feedbackBtn.textContent = '❌ 这不是任务';
  feedbackBtn.style.padding = '6px 16px';
  feedbackBtn.style.fontSize = '13px';
  feedbackBtn.style.border = '1px solid #888';
  feedbackBtn.style.color = '#666';
  feedbackBtn.style.background = '#fff';
  feedbackBtn.style.borderRadius = '16px';
  feedbackBtn.style.cursor = 'pointer';
  feedbackBtn.style.transition = 'all 0.2s';
  feedbackBtn.onmouseenter = () => { feedbackBtn.style.background = '#f5f5f5'; };
  feedbackBtn.onmouseleave = () => { feedbackBtn.style.background = '#fff'; };

  feedbackBtn.onclick = async () => {
    feedbackBtn.disabled = true;
    feedbackBtn.textContent = '已记录';
    feedbackBtn.style.color = '#999';
    feedbackBtn.style.borderColor = '#ccc';
    feedbackBtn.style.cursor = 'default';

    if (cancelBtn.parentNode) {
      cancelBtn.disabled = true;
      cancelBtn.textContent = '已取消';
      cancelBtn.style.color = '#ccc';
      cancelBtn.style.borderColor = '#ccc';
      cancelBtn.style.cursor = 'default';
    }

    try {
      const token = localStorage.getItem('sases_token');
      await fetch('/swarm/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          task_id: taskId,
          original_input: originalInput,
          feedback_type: 'false_positive'
        })
      });
    } catch (e) {
      console.error('反馈失败', e);
    }
    setTimeout(() => {
      if (wrap.parentNode) wrap.remove();
    }, 1500);
  };

  if (swarmStatus === 'planned') {
    wrap.appendChild(cancelBtn);
  }
  wrap.appendChild(feedbackBtn);

  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;

  setTimeout(() => {
    if (wrap.parentNode) wrap.remove();
  }, 10000);
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


window.__sasesClearAttachment = function() {
  if (window.chatState) window.chatState.pendingAttachment = null;
  const el = document.getElementById('attachment-preview');
  if (el) { el.style.display = 'none'; el.innerHTML = ''; }
};
window.sendTransfer = sendTransfer;


window.__sasesUploadFile = async (file) => {
  if (!file) return;
  if (!chatState.conversationId) {
    alert('请先进入会话');
    return;
  }
  try {
    const res = await api.uploadFile(file);
    if (!res || !res.url) {
      alert('上传失败');
      return;
    }
    const _content = '[FILE]:' + res.url + '|' + (file.name || 'file') + '|' + (file.size || 0);
    appendMessage('user', _content, chatState.senderAgentId ? '智能体' : '我', null, new Date().toISOString(), false, chatState);
    await api.sendMessage({
      conversation_id: chatState.conversationId,
      agent_id: chatState.agentId,
      content: _content,
      sender_agent_id: chatState.senderAgentId,
      mode: chatState.mode
    });
  } catch (e) {
    alert('上传失败：' + (e.message || '未知错误'));
  }
};


window.__sasesUploadImage = async (file) => {
  if (!file) return;
  if (!chatState.conversationId) {
    alert('请先进入会话');
    return;
  }
  try {
    const res = await api.uploadImage(file);
    if (!res || !res.url) {
      alert('上传失败');
      return;
    }
    await api.sendMessage({
      conversation_id: chatState.conversationId,
      agent_id: chatState.agentId,
      content: '[IMAGE]:' + res.url,
      sender_agent_id: chatState.senderAgentId,
      mode: chatState.mode
    });
    await loadMessages(chatState.conversationId);
  } catch (e) {
    alert('上传失败：' + (e.message || '未知错误'));
  }
};

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
  chatState.senderAgentId = localStorage.getItem('sases_sender_agent_id') || null;
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
    // (历史 proposed 卡片暂不自动渲染，避免重复)

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