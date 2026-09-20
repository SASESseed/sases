// static/modules/chat_ui.js

// ========== 协议消息过滤（v0.17.0） ==========
const HIDDEN_PREFIXES = ['[TASK]:', '[TASK_DRAFT]:', '[STEP_DONE]:', '[RETRY_TASK]:'];

export function isProtocolMessage(content) {
  if (typeof content !== 'string') return false;
  for (const p of HIDDEN_PREFIXES) {
    if (content.startsWith(p)) return true;
  }
  return false;
}

export function stripSummaryPrefix(content) {
  if (typeof content === 'string' && content.startsWith('[SUMMARY]:')) {
    return content.substring('[SUMMARY]:'.length);
  }
  return content;
}


// ========== HTML 转义 ==========
function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ========== 指令消息渲染 ==========
export function appendWorkMessage(role, content, senderName = null) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;

  const wrapper = document.createElement('div');
  wrapper.style.display = 'flex';
  wrapper.style.flexDirection = 'row';
  wrapper.style.alignItems = 'flex-start';
  wrapper.style.margin = '8px 12px';
  if (role === 'user') {
    wrapper.style.justifyContent = 'flex-end';
  } else {
    wrapper.style.justifyContent = 'flex-start';
  }

  const avatar = document.createElement('div');
  avatar.style.width = '36px';
  avatar.style.height = '36px';
  avatar.style.borderRadius = '50%';
  avatar.style.background = role === 'user' ? '#007aff' : '#e0e0e0';
  avatar.style.color = role === 'user' ? '#fff' : '#333';
  avatar.style.display = 'flex';
  avatar.style.alignItems = 'center';
  avatar.style.justifyContent = 'center';
  avatar.style.flexShrink = '0';
  avatar.style.fontSize = '16px';
  avatar.textContent = (senderName || (role === 'user' ? '我' : 'AI')).charAt(0).toUpperCase();

  const bubble = document.createElement('div');
  bubble.style.maxWidth = '70%';
  bubble.style.padding = '10px 14px';
  bubble.style.borderRadius = role === 'user' ? '12px 2px 12px 12px' : '2px 12px 12px 12px';
  bubble.style.wordBreak = 'break-word';
  bubble.style.whiteSpace = 'pre-wrap';
  bubble.style.fontSize = '15px';
  if (role === 'user') {
    bubble.style.background = '#007aff';
    bubble.style.color = '#fff';
    bubble.innerHTML = `<div style="font-weight:600;">💻 ${escapeHtml(content)}</div>`;
  } else {
    bubble.style.background = '#f0f0f0';
    bubble.style.color = '#333';
    bubble.innerHTML = `<div style="font-weight:600; margin-bottom:6px;">📋 执行结果</div><pre style="margin:0; white-space:pre-wrap; word-break:break-word;">${escapeHtml(content)}</pre>`;
  }

  if (role === 'user') {
    wrapper.appendChild(bubble);
    wrapper.appendChild(avatar);
  } else {
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
  }

  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

// ========== 普通消息元素创建 ==========
export function createMessageElement(role, content, senderName, messageId, timeIso, isPending = false, skipTimeTag = false, chatState = null) {
  if (isProtocolMessage(content)) {
    const empty = document.createElement('div');
    empty.style.display = 'none';
    return empty;
  }
  content = stripSummaryPrefix(content);
    if (typeof content === 'string' && content.startsWith('[RED_PACKET]:')) { return renderRedPacketBubble(content); }
  if (typeof content === 'string' && content.startsWith('[IMAGE]:')) { return renderImageBubble(content, role, senderName); }
  const wrapper = document.createElement('div');
  wrapper.style.display = 'flex';
  wrapper.style.flexDirection = 'row';
  wrapper.style.alignItems = 'flex-start';
  wrapper.style.margin = '8px 12px';
  wrapper.dataset.messageId = messageId || '';
  wrapper.dataset.role = role;
  wrapper.dataset.senderName = senderName || (role === 'user' ? '我' : 'AI');
  wrapper.dataset.content = content;

  if (role === 'user') {
    wrapper.style.justifyContent = 'flex-end';
  } else {
    wrapper.style.justifyContent = 'flex-start';
  }

  const avatar = document.createElement('div');
  avatar.style.width = '36px';
  avatar.style.height = '36px';
  avatar.style.borderRadius = '50%';
  avatar.style.background = role === 'user' ? '#007aff' : '#e0e0e0';
  avatar.style.color = role === 'user' ? '#fff' : '#333';
  avatar.style.display = 'flex';
  avatar.style.alignItems = 'center';
  avatar.style.justifyContent = 'center';
  avatar.style.flexShrink = '0';
  avatar.style.fontSize = '16px';
  avatar.textContent = (senderName || (role === 'user' ? '我' : 'AI')).charAt(0).toUpperCase();

  const bubble = document.createElement('div');
  bubble.style.maxWidth = '70%';
  bubble.style.padding = '10px 14px';
  bubble.style.borderRadius = role === 'user' ? '12px 2px 12px 12px' : '2px 12px 12px 12px';
  bubble.style.wordBreak = 'break-word';
  bubble.style.whiteSpace = 'pre-wrap';
  bubble.style.fontSize = '15px';
  if (role === 'user') {
    bubble.style.background = '#007aff';
    bubble.style.color = '#fff';
  } else {
    bubble.style.background = '#f0f0f0';
    bubble.style.color = '#333';
  }

  if (role === 'user' && senderName && senderName !== '我') {
    bubble.innerHTML = `<span style="font-weight:600;">${escapeHtml(senderName)}:</span> ${escapeHtml(content)}`;
  } else {
    bubble.textContent = content;
  }

  if (role === 'user') {
    wrapper.appendChild(bubble);
    wrapper.appendChild(avatar);
    if (isPending) {
      const status = document.createElement('span');
      status.style.fontSize = '12px';
      status.style.color = '#999';
      status.style.alignSelf = 'center';
      status.style.marginRight = '8px';
      status.textContent = '发送中...';
      wrapper.appendChild(status);
    }
  } else {
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
  }

  return wrapper;
}

// ========== 消息插入与时间标签 ==========
export function appendMessage(role, content, senderName = null, messageId = null, timeIso = null, isPending = false, chatState = null) {
  if (isProtocolMessage(content)) return;
  const messages = document.getElementById('chat-messages');
  if (!messages) return;

  if (timeIso && chatState) {
    insertTimeTag(timeIso, chatState);
  }

  const wrapper = createMessageElement(role, content, senderName, messageId, timeIso, isPending, false, chatState);
  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;

  if (role === 'assistant' && typeof window.attachLongPress === 'function') {
    window.attachLongPress(wrapper, chatState);
  if (wrapper && wrapper.querySelector && wrapper.querySelector('.red-packet-bubble')) {
    const bubble = wrapper.querySelector('.red-packet-bubble');
    bubble.addEventListener('click', async () => {
      const tx = bubble.dataset.redPacketTx;
      if (!tx) return;
      if (!confirm('确定领取这个红包？')) return;
      try {
        await api.claimRedPacket(parseInt(tx));
        alert('领取成功');
      } catch (e) {
        alert('领取失败：' + (e.message || '未知错误'));
      }
    });
  }
  }
}


export function insertTimeTag(timeIso, chatState) {
  const container = document.getElementById('chat-messages');
  if (!container || !chatState) return;
  if (!chatState.lastMessageTime) {
    chatState.lastMessageTime = timeIso;
    return;
  }
  const diff = new Date(timeIso) - new Date(chatState.lastMessageTime);
  if (Math.abs(diff) > 5 * 60 * 1000) {
    const tag = document.createElement('div');
    tag.style.textAlign = 'center';
    tag.style.fontSize = '12px';
    tag.style.color = '#999';
    tag.style.margin = '8px 0';
    tag.textContent = formatTime(timeIso);
    container.appendChild(tag);
  }
  chatState.lastMessageTime = timeIso;
}

export function formatTime(isoString) {
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

// ========== 消息状态更新 ==========
export function renderImageBubble(content, role = 'user', senderName = null) {
  const url = content.substring('[IMAGE]:'.length);
  const wrapper = document.createElement('div');
  wrapper.style.display = 'flex';
  wrapper.style.flexDirection = 'row';
  wrapper.style.alignItems = 'flex-start';
  wrapper.style.margin = '8px 12px';
  wrapper.style.justifyContent = (role === 'user') ? 'flex-end' : 'flex-start';
  const imgBox = document.createElement('div');
  imgBox.style.maxWidth = '180px';
  imgBox.style.borderRadius = '8px';
  imgBox.style.overflow = 'hidden';
  imgBox.style.cursor = 'pointer';
  const img = document.createElement('img');
  img.src = url;
  img.style.display = 'block';
  img.style.width = '100%';
  img.style.maxHeight = '240px';
  img.onclick = () => window.open(url, '_blank');
  imgBox.appendChild(img);
  const avatar = document.createElement('div');
  avatar.style.width = '36px';
  avatar.style.height = '36px';
  avatar.style.borderRadius = '50%';
  avatar.style.background = role === 'user' ? '#007aff' : '#e0e0e0';
  avatar.style.color = role === 'user' ? '#fff' : '#333';
  avatar.style.display = 'flex';
  avatar.style.alignItems = 'center';
  avatar.style.justifyContent = 'center';
  avatar.style.flexShrink = '0';
  avatar.style.fontSize = '16px';
  avatar.style.marginLeft = role === 'user' ? '8px' : '0';
  avatar.style.marginRight = role === 'user' ? '0' : '8px';
  avatar.textContent = (senderName || (role === 'user' ? '我' : 'AI')).charAt(0).toUpperCase();
  if (role === 'user') {
    wrapper.appendChild(imgBox);
    wrapper.appendChild(avatar);
  } else {
    wrapper.appendChild(avatar);
    wrapper.appendChild(imgBox);
  }
  return wrapper;
}


export function renderRedPacketBubble(content) {
  let data = {};
  try { data = JSON.parse(content.substring('[RED_PACKET]:'.length)); } catch (e) {}
  const div = document.createElement('div');
  div.className = 'red-packet-bubble';
  div.dataset.redPacketTx = data.tx_id || '';
  div.innerHTML = '<div style="font-size:13px;opacity:0.9;">🧧 红包</div><div style="font-size:20px;font-weight:700;margin-top:4px;">¥' + (data.amount || 0) + '</div>' + (data.message ? '<div style="font-size:12px;opacity:0.85;margin-top:4px;">' + data.message + '</div>' : '');
  return div;
}

export function updateMessageStatus(messageId, status) {
  const wrapper = document.querySelector(`[data-message-id="${messageId}"]`);
  if (!wrapper) return;
  const existingStatus = wrapper.querySelector('.message-status');
  if (existingStatus) {
    if (status === 'sent') {
      existingStatus.remove();
    } else if (status === 'failed') {
      existingStatus.style.fontSize = '12px';
      existingStatus.style.color = '#ff3b30';
      existingStatus.style.alignSelf = 'center';
      existingStatus.style.marginRight = '8px';
      existingStatus.textContent = '发送失败';
      const retryBtn = document.createElement('button');
      retryBtn.textContent = '重试';
      retryBtn.style.fontSize = '12px';
      retryBtn.style.marginLeft = '4px';
      retryBtn.addEventListener('click', () => {
        const content = wrapper.dataset.content;
        const input = document.getElementById('chat-input');
        input.value = content;
        if (typeof window.updateSendButtonVisibility === 'function') {
          window.updateSendButtonVisibility();
        }
        if (typeof window.sendMessage === 'function') {
          window.sendMessage();
        }
        wrapper.remove();
      });
      existingStatus.appendChild(retryBtn);
    }
  } else if (status === 'failed') {
    const statusEl = document.createElement('span');
    statusEl.style.fontSize = '12px';
    statusEl.style.color = '#ff3b30';
    statusEl.style.alignSelf = 'center';
    statusEl.style.marginRight = '8px';
    statusEl.textContent = '发送失败';
    wrapper.appendChild(statusEl);
  }
}