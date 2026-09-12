// static/modules/chat_menu.js
import { api } from './api.js';
import { openIdentitySwitch } from './chat_identity.js';

// ========== 长按菜单 ==========
export function createContextMenu() {
  const oldMenu = document.getElementById('message-context-menu');
  if (oldMenu) oldMenu.remove();

  const menu = document.createElement('div');
  menu.id = 'message-context-menu';
  menu.style.position = 'fixed';
  menu.style.zIndex = '9999';
  menu.style.background = '#fff';
  menu.style.borderRadius = '8px';
  menu.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
  menu.style.display = 'none';
  document.body.appendChild(menu);
}

export function showContextMenu(x, y, wrapper, chatState) {
  const menu = document.getElementById('message-context-menu');
  if (!menu) return;
  menu.innerHTML = `
    <div class="context-menu-item" data-action="quote" style="padding:10px 16px; cursor:pointer;">引用</div>
    <div class="context-menu-item" data-action="reply" style="padding:10px 16px; cursor:pointer;">帮我回复</div>
  `;
  menu.style.display = 'block';
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';

  menu.querySelector('[data-action="quote"]').addEventListener('click', () => {
    chatState.pendingQuote = wrapper.dataset.content;
    showQuoteBar(chatState.pendingQuote, chatState);
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
        if (typeof window.updateSendButtonVisibility === 'function') {
          window.updateSendButtonVisibility();
        }
        input.focus();
      }
    } catch (e) {
      alert('生成回复失败：' + e.message);
    }
    closeContextMenu();
  });
}

export function closeContextMenu() {
  const menu = document.getElementById('message-context-menu');
  if (menu) menu.style.display = 'none';
}

export function attachLongPress(wrapper, chatState) {
  let timer = null;
  wrapper.addEventListener('touchstart', (e) => {
    const touch = e.touches[0];
    timer = setTimeout(() => {
      showContextMenu(touch.clientX, touch.clientY, wrapper, chatState);
    }, 800);
  }, { passive: true });

  wrapper.addEventListener('touchend', () => {
    if (timer) clearTimeout(timer);
  });
  wrapper.addEventListener('touchmove', () => {
    if (timer) clearTimeout(timer);
  });
}

// 将 attachLongPress 挂到 window，方便 chat_ui.js 调用
window.attachLongPress = attachLongPress;

// ========== 引用条 ==========
export function showQuoteBar(text, chatState) {
  let bar = document.getElementById('quote-bar');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'quote-bar';
    bar.style.display = 'flex';
    bar.style.alignItems = 'center';
    bar.style.justifyContent = 'space-between';
    bar.style.padding = '8px 12px';
    bar.style.background = '#f7f7f7';
    bar.style.borderRadius = '8px';
    bar.style.margin = '0 12px 8px';
    bar.innerHTML = `
      <span class="quote-text" style="flex:1; color:#666; font-size:14px;"></span>
      <button class="quote-close" style="background:none; border:none; font-size:18px; cursor:pointer;">×</button>
    `;
    const inputArea = document.querySelector('.chat-input-area');
    inputArea.parentElement.insertBefore(bar, inputArea);
    bar.querySelector('.quote-close').addEventListener('click', () => {
      chatState.pendingQuote = null;
      hideQuoteBar();
    });
  }
  bar.querySelector('.quote-text').textContent = text;
  bar.style.display = 'flex';
}

export function hideQuoteBar() {
  const bar = document.getElementById('quote-bar');
  if (bar) bar.style.display = 'none';
}

// ========== 聊天信息页 ==========
export function openChatInfo(chatState) {
  const chatName = document.getElementById('chat-window-title').textContent;
  const contentHtml = `
    <div class="chat-info-header">
      <div class="chat-info-avatar">${chatName.charAt(0)}</div>
      <div class="chat-info-name">${chatName}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="switch-identity-entry">
        <span class="menu-label">切换身份</span>
        <span class="menu-value" id="current-identity-text">${chatState.senderAgentId ? '智能体身份' : '以本人身份'}</span>
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
    document.getElementById('switch-identity-entry').addEventListener('click', () => openIdentitySwitch(chatState, api));
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

// ========== 加号面板 ==========
export function toggleChatPlusPanel() {
  const panel = document.getElementById('chat-plus-panel');
  if (!panel) return;
  if (panel.style.display === 'block') {
    closeChatPlusPanel();
  } else {
    openChatPlusPanel();
  }
}

export function openChatPlusPanel() {
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

export function closeChatPlusPanel() {
  const panel = document.getElementById('chat-plus-panel');
  if (panel) panel.style.display = 'none';
}

// 点击外部关闭长按菜单
document.addEventListener('click', (e) => {
  const menu = document.getElementById('message-context-menu');
  if (menu && !menu.contains(e.target)) {
    closeContextMenu();
  }
});