// static/modules/contacts.js
import { api } from './api.js';
import { openChatWindow } from './chat.js';
import { openGroupChat } from './group_chat.js';
import { initPullToRefresh } from './utils.js';
import { t } from './i18n.js';

let initialized = false;
let myAgents = [];
let friendAgents = [];
let touchStartX = 0;
let touchStartY = 0;
let currentOpenRow = null;

export function initContacts() {
  const container = document.getElementById('contacts-list');
  if (!container) return;
  renderContacts(container);
}

function getPinyinInitial(name) {
  if (window.pinyinPro) {
    const pinyin = window.pinyinPro.pinyin(name, { pattern: 'first', toneType: 'none' });
    if (pinyin && pinyin.length > 0) return pinyin[0].toUpperCase();
  }
  return name.charAt(0).toUpperCase();
}

function hashColor(input) {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    hash = input.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 65%, 55%)`;
}

function getStatusDotClass(agent) {
  if (agent.detail && agent.detail.toLowerCase().includes('offline')) return 'status-dot offline';
  if (agent.detail && agent.detail.toLowerCase().includes('error')) return 'status-dot error';
  return 'status-dot online';
}

async function fetchAgents() {
  try {
    const myData = await api.listMyAgents();
    myAgents = myData.agents || [];
  } catch (e) {
    console.warn('获取智能体列表失败', e);
  }
  try {
    const friendData = await api.listFriendAgents();
    friendAgents = friendData.friends || [];
  } catch (e) {
    console.warn('获取好友智能体失败', e);
  }
}

function generateAgentRow(agent, type) {
  const bgColor = hashColor(agent.agent_id);
  const statusClass = getStatusDotClass(agent);
  const name = type === 'my' ? `${agent.name}${agent.type === 'local' ? ' <span style="color:green;font-size:12px;">授粉+2</span>' : ''}` : agent.name;
  const desc = type === 'my' ? (agent.detail || agent.capability) : `${agent.owner} · ${agent.detail}`;
  const actions = type === 'my' ? `
    <button class="swipe-btn share-btn" data-action="share">${t('share_settings')}</button>
    <button class="swipe-btn delete-btn" data-action="delete">${t('delete')}</button>
  ` : `
    <button class="swipe-btn complain-btn" data-action="complain">${t('complain')}</button>
    <button class="swipe-btn delete-btn" data-action="delete">${t('delete')}</button>
  `;

  return `
    <div class="swipe-row" data-agent-id="${agent.agent_id}" data-agent-name="${agent.name}" data-agent-type="${type}">
      <div class="agent-row">
        <div class="agent-avatar" style="background: ${bgColor};">
          ${agent.name.charAt(0)}
          <span class="${statusClass}"></span>
        </div>
        <div class="agent-info">
          <div class="agent-name">${name}</div>
          <div class="agent-desc">${desc}</div>
          <div class="agent-id-display" style="font-size:12px;color:#999;">ID: ${agent.agent_id}</div>
        </div>
      </div>
      <div class="swipe-actions">
        ${actions}
      </div>
    </div>
  `;
}

function closeAllSwipe() {
  if (currentOpenRow) {
    currentOpenRow.classList.remove('swipe-open');
    currentOpenRow = null;
  }
}

function handleTouchStart(e) {
  const touch = e.touches[0];
  touchStartX = touch.clientX;
  touchStartY = touch.clientY;
}

function handleTouchEnd(e) {
  const row = e.currentTarget;
  const touch = e.changedTouches[0];
  const deltaX = touch.clientX - touchStartX;
  const deltaY = touch.clientY - touchStartY;
  if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
    if (deltaX < 0) {
      closeAllSwipe();
      row.classList.add('swipe-open');
      currentOpenRow = row;
    } else {
      row.classList.remove('swipe-open');
      if (currentOpenRow === row) currentOpenRow = null;
    }
  }
}

async function renderContacts(container) {
  container.innerHTML = '<div class="subpage-placeholder">加载中...</div>';
  await fetchAgents();

  let myAgentsHtml = '';
  if (myAgents.length === 0) {
    myAgentsHtml = `<div class="me-menu-item" style="color:#999;">${t('empty_agents')}</div>`;
  } else {
    myAgentsHtml = '<div class="me-menu">';
    myAgents.forEach(agent => {
      myAgentsHtml += generateAgentRow(agent, 'my');
    });
    myAgentsHtml += '</div>';
  }

  let friendAgentsHtml = '';
  let letterIndexHtml = '';
  if (friendAgents.length === 0) {
    friendAgentsHtml = `<div class="me-menu-item" style="color:#999;">${t('no_friend_agents')}</div>`;
  } else {
    const grouped = {};
    friendAgents.forEach(agent => {
      const initial = getPinyinInitial(agent.name);
      if (!grouped[initial]) grouped[initial] = [];
      grouped[initial].push(agent);
    });
    const sortedInitials = Object.keys(grouped).sort();
    friendAgentsHtml = '<div class="me-menu">';
    sortedInitials.forEach(initial => {
      friendAgentsHtml += `<div class="letter-title" data-letter="${initial}">${initial}</div>`;
      grouped[initial].sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN')).forEach(agent => {
        friendAgentsHtml += generateAgentRow(agent, 'friend');
      });
    });
    friendAgentsHtml += '</div>';

    letterIndexHtml = '<div class="letter-index">';
    sortedInitials.forEach(initial => {
      letterIndexHtml += `<div class="letter-index-item" data-letter="${initial}">${initial}</div>`;
    });
    letterIndexHtml += '</div>';
  }

  container.innerHTML = `
    <div class="subpage-search-bar" style="margin-bottom:10px;">
      <input type="text" id="contact-search-input" class="search-input" placeholder="${t('search_placeholder')}">
    </div>
    <div class="me-menu">
      <div class="me-menu-item" data-entry="new-agent">🧑‍🤝‍🧑 ${t('new_agent')}</div>
      <div class="me-menu-item" data-entry="api-agent">🔑 ${t('api_agent')}</div>
      <div class="me-menu-item" data-entry="group-chat">👥 ${t('group_chat')}</div>
    </div>
    <div class="section-title">${t('my_agents')}</div>
    ${myAgentsHtml}
    <div class="section-title">${t('friend_agents')}</div>
    <div class="friend-list-wrapper">
      ${friendAgentsHtml}
      ${letterIndexHtml}
    </div>
  `;

  // 初始化下拉刷新
  initPullToRefresh(container, async () => {
    await renderContacts(container);
  });

  // 绑定搜索过滤
  const searchInput = document.getElementById('contact-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      filterAgents(searchInput.value.trim().toLowerCase());
    });
  }

  // 绑定置顶入口
  container.querySelectorAll('[data-entry]').forEach(item => {
    item.addEventListener('click', () => {
      const type = item.dataset.entry;
      if (type === 'new-agent') openNewAgentPage();
      else if (type === 'api-agent') { if (window.openModelManagement) window.openModelManagement(); }
      else if (type === 'group-chat') openGroupChatList();
    });
  });

  // 绑定智能体行点击和触摸
  container.querySelectorAll('.swipe-row').forEach(row => {
    row.addEventListener('click', (e) => {
      if (e.target.closest('.swipe-btn')) return;
      closeAllSwipe();
      const agentId = row.dataset.agentId;
      const agentName = row.dataset.agentName;
      const agentType = row.dataset.agentType;
      openAgentInfo(agentId, agentName, agentType);
    });

    row.addEventListener('touchstart', handleTouchStart, { passive: true });
    row.addEventListener('touchend', handleTouchEnd, { passive: true });

    const actionBtns = row.querySelectorAll('.swipe-btn');
    actionBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const action = btn.dataset.action;
        const agentId = row.dataset.agentId;
        const agentName = row.dataset.agentName;
        const agentType = row.dataset.agentType;
        handleSwipeAction(action, agentId, agentName, agentType);
      });
    });
  });

  // 绑定字母索引
  container.querySelectorAll('.letter-index-item').forEach(item => {
    item.addEventListener('click', () => {
      const letter = item.dataset.letter;
      const titleElements = container.querySelectorAll('.letter-title');
      for (const titleEl of titleElements) {
        if (titleEl.textContent === letter) {
          titleEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
          break;
        }
      }
    });
  });
}

function handleSwipeAction(action, agentId, agentName, agentType) {
  closeAllSwipe();
  if (action === 'share') {
    alert(t('share_settings') + ': ' + agentName);
  } else if (action === 'delete') {
    if (confirm(`${t('delete_confirm')} "${agentName}"?`)) {
      alert(t('delete_success'));
      renderContacts(document.getElementById('contacts-list'));
    }
  } else if (action === 'complain') {
    alert(t('complain') + ' ' + t('coming_soon'));
  }
}

function filterAgents(query) {
  const container = document.getElementById('contacts-list');
  if (!container) return;
  const rows = container.querySelectorAll('.swipe-row');
  rows.forEach(row => {
    const name = row.dataset.agentName?.toLowerCase() || '';
    const desc = row.querySelector('.agent-desc')?.textContent?.toLowerCase() || '';
    const match = name.includes(query) || desc.includes(query);
    row.style.display = match ? '' : 'none';
  });
  const titles = container.querySelectorAll('.letter-title');
  titles.forEach(title => {
    let next = title.nextElementSibling;
    let hasVisible = false;
    while (next && !next.classList.contains('letter-title')) {
      if (next.classList.contains('swipe-row') && next.style.display !== 'none') {
        hasVisible = true;
        break;
      }
      next = next.nextElementSibling;
    }
    title.style.display = hasVisible ? '' : 'none';
  });
}

// ==================== 智能体详情页 ====================
function openAgentInfo(agentId, agentName, agentType) {
  let remark = localStorage.getItem(`agent_remark_${agentId}`) || '';
  let tags = localStorage.getItem(`agent_tags_${agentId}`) || '未设置';
  let sign = localStorage.getItem(`agent_sign_${agentId}`) || '这个智能体很懒，什么都没留下';

  const typeLabel = agentType === 'my' ? t('my_agents') : t('friend_agents');
  const priceText = agentType === 'my' ? t('free_for_self') : t('ask_provider');

  const contentHtml = `
    <div class="agent-detail-header">
      <div class="agent-avatar-large" style="background: ${hashColor(agentId)};">${agentName.charAt(0)}</div>
      <div class="agent-detail-name">${agentName}</div>
      ${remark ? `<div class="agent-detail-remark">${t('remark')}: ${remark}</div>` : ''}
      <div class="agent-detail-id">SASES ID: ${agentId}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">${t('type')}</span><span class="menu-value">${typeLabel}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('call_price_label')}</span><span class="menu-value">${priceText}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('capability')}</span><span class="menu-value">${agentType === 'my' ? '本地模型/API' : '未知'}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('status')}</span><span class="menu-value">${t('online')}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('tags')}</span><span class="menu-value">${tags}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('signature_label')}</span><span class="menu-value">${sign}</span></div>
    </div>
    <div class="agent-detail-actions" style="margin-top:16px;">
      <button id="send-message-btn" class="detail-action-btn">💬 ${t('send_message')}</button>
    </div>
  `;

  window.openSubpage(agentName, contentHtml, {
    showMore: true,
    onMore: () => openAgentActionPage(agentId, agentName, agentType)
  });

  setTimeout(() => {
    const sendBtn = document.getElementById('send-message-btn');
    if (sendBtn) {
      sendBtn.onclick = () => {
        window.closeSubpage();
        openChatWindow(`agent-${agentId}`, agentName, agentId, agentType);
      };
    }
  }, 100);
}

function openAgentActionPage(agentId, agentName, agentType) {
  const actions = agentType === 'my' ? [
    { label: t('set_remark'), action: () => { const v = prompt(t('set_remark')); if (v) { localStorage.setItem(`agent_remark_${agentId}`, v); alert(t('remark_saved')); } } },
    { label: t('set_tags'), action: () => { const v = prompt(t('set_tags')); if (v) { localStorage.setItem(`agent_tags_${agentId}`, v); alert(t('tags_saved')); } } },
    { label: t('set_signature'), action: () => { const v = prompt(t('set_signature')); if (v) { localStorage.setItem(`agent_sign_${agentId}`, v); alert(t('signature_saved')); } } },
    { label: t('delete_agent'), action: () => { if (confirm(`${t('delete_confirm')} "${agentName}"?`)) alert(t('delete_success')); } }
  ] : [
    { label: t('set_remark'), action: () => { const v = prompt(t('set_remark')); if (v) { localStorage.setItem(`agent_remark_${agentId}`, v); alert(t('remark_saved')); } } },
    { label: t('set_tags'), action: () => { const v = prompt(t('set_tags')); if (v) { localStorage.setItem(`agent_tags_${agentId}`, v); alert(t('tags_saved')); } } },
    { label: t('complain'), action: () => alert(t('complain') + ' ' + t('coming_soon')) },
    { label: t('delete_friend'), action: () => { if (confirm(`${t('delete_confirm')} "${agentName}"?`)) alert(t('delete_success')); } }
  ];

  let listHtml = '<div class="me-menu">';
  actions.forEach(item => {
    listHtml += `<div class="me-menu-item agent-action-item"><span class="menu-label">${item.label}</span><span class="menu-arrow">›</span></div>`;
  });
  listHtml += '</div>';

  window.openSubpage(t('more_actions'), listHtml, { showMore: false });

  setTimeout(() => {
    document.querySelectorAll('.agent-action-item').forEach((el, index) => {
      el.addEventListener('click', () => {
        window.closeSubpage();
        actions[index].action();
      });
    });
  }, 100);
}

// ==================== 新智能体页面 ====================
function openNewAgentPage() {
  const contentHtml = `
    <div class="subpage-search-bar">
      <input type="text" class="search-input" id="agent-search-input" placeholder="${t('search_agent_placeholder')}">
      <button class="search-btn" id="search-agent-btn">${t('search')}</button>
    </div>
    <div id="agent-search-results" class="me-menu"></div>
    <div class="section-title" style="margin-top:20px;">${t('request_received')}</div>
    <div id="friend-requests-list" class="me-menu"></div>
  `;
  window.openSubpage(t('new_friend'), contentHtml, {
    showMore: true,
    onMore: () => window.openSubpage(t('add_friend'), `<div class="subpage-placeholder">${t('add_friend_placeholder')}</div>`)
  });

  setTimeout(() => {
    document.getElementById('search-agent-btn').addEventListener('click', () => {
      const q = document.getElementById('agent-search-input').value.trim();
      if (q) searchAgents(q);
    });
    document.getElementById('agent-search-input').addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && document.getElementById('agent-search-input').value.trim()) searchAgents(document.getElementById('agent-search-input').value.trim());
    });
    loadFriendRequests();
  }, 100);
}

async function searchAgents(q) {
  const resultsContainer = document.getElementById('agent-search-results');
  resultsContainer.innerHTML = '<div class="subpage-placeholder">搜索中...</div>';
  try {
    const data = await api.searchAgents(q, true);
    const results = data.results || [];
    if (results.length === 0) {
      resultsContainer.innerHTML = '<div class="subpage-placeholder">无结果</div>';
      return;
    }
    let html = '';
    results.forEach(agent => {
      html += `
        <div class="me-menu-item agent-row" data-agent-id="${agent.agent_id}" data-agent-name="${agent.name}" data-price="${agent.price}">
          <div class="agent-avatar" style="background: ${hashColor(agent.agent_id)};">${agent.name.charAt(0)}</div>
          <div class="agent-info">
            <div class="agent-name">${agent.name}</div>
            <div class="agent-desc">${agent.owner} · ${agent.detail}</div>
            <div class="agent-id-display" style="font-size:12px;color:#999;">ID: ${agent.agent_id}</div>
          </div>
          <button class="add-friend-btn" data-agent-id="${agent.agent_id}">${t('add_friend')}</button>
        </div>
      `;
    });
    resultsContainer.innerHTML = html;

    resultsContainer.querySelectorAll('.add-friend-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const agentId = btn.dataset.agentId;
        await sendFriendRequest(agentId);
      });
    });
  } catch (e) {
    resultsContainer.innerHTML = `<div class="subpage-placeholder">搜索失败：${e.message}</div>`;
  }
}

async function sendFriendRequest(agentId) {
  try {
    await api.sendFriendRequest(agentId);
    alert(t('request_sent'));
  } catch (e) {
    alert(t('send_failed') + ': ' + e.message);
  }
}

async function loadFriendRequests() {
  const container = document.getElementById('friend-requests-list');
  if (!container) return;
  container.innerHTML = '<div class="subpage-placeholder">加载中...</div>';
  try {
    const data = await api.getFriendRequests();
    const requests = data.requests || [];
    if (requests.length === 0) {
      container.innerHTML = `<div class="subpage-placeholder">${t('no_requests')}</div>`;
      return;
    }
    let html = '';
    requests.forEach(req => {
      html += `
        <div class="me-menu-item friend-request-item">
          <div class="agent-avatar">${req.requester_name.charAt(0)}</div>
          <div class="agent-info">
            <div class="agent-name">${req.requester_name}</div>
            <div class="agent-desc">${t('wants_add_agent')}: ${req.agent_name}</div>
          </div>
          <button class="accept-request-btn" data-request-id="${req.id}">${t('accept')}</button>
          <button class="reject-request-btn" data-request-id="${req.id}">${t('reject')}</button>
        </div>
      `;
    });
    container.innerHTML = html;

    container.querySelectorAll('.accept-request-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const requestId = btn.dataset.requestId;
        try {
          await api.acceptFriendRequest(requestId);
          alert(t('accepted'));
          loadFriendRequests();
        } catch (err) { alert(t('operation_failed') + ': ' + err.message); }
      });
    });
    container.querySelectorAll('.reject-request-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const requestId = btn.dataset.requestId;
        try {
          await api.rejectFriendRequest(requestId);
          alert(t('rejected'));
          loadFriendRequests();
        } catch (err) { alert(t('operation_failed') + ': ' + err.message); }
      });
    });
  } catch (e) {
    container.innerHTML = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }
}

// ==================== 群聊列表 ====================
async function openGroupChatList() {
  let groupsHtml = '<div class="subpage-placeholder">加载中...</div>';
  window.openSubpage(t('group_chat'), groupsHtml);

  try {
    const data = await api.listMyGroups();
    const groups = data.groups || [];
    if (groups.length === 0) {
      groupsHtml = `<div class="subpage-placeholder">${t('no_groups')}</div>`;
    } else {
      groupsHtml = '<div class="me-menu">';
      groups.forEach(group => {
        groupsHtml += `
          <div class="me-menu-item group-item" data-group-id="${group.id}" data-group-name="${group.name}">
            <span class="menu-icon">👥</span>
            <div class="menu-text">
              <div class="menu-title">${group.name}</div>
              <div class="menu-desc">${group.member_count} ${t('member_count')}</div>
            </div>
          </div>
        `;
      });
      groupsHtml += '</div>';
    }
  } catch (e) {
    groupsHtml = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }

  const contentHtml = `
    <div style="display:flex;gap:8px;margin-bottom:12px;">
      <input type="text" id="new-group-name" class="market-input" placeholder="${t('group_name')}" style="flex:1;">
      <button id="create-group-btn" class="save-btn" style="width:auto;">${t('create_group')}</button>
    </div>
    ${groupsHtml}
  `;
  document.getElementById('subpage-content').innerHTML = contentHtml;

  const createBtn = document.getElementById('create-group-btn');
  if (createBtn) {
    createBtn.addEventListener('click', async () => {
      const name = document.getElementById('new-group-name').value.trim();
      if (!name) { alert(t('please_input_all')); return; }
      try {
        await api.createGroup(name);
        alert(t('create_group_success'));
        openGroupChatList();
      } catch (e) {
        alert(t('create_group_failed') + ': ' + e.message);
      }
    });
  }

  document.querySelectorAll('.group-item').forEach(item => {
    item.addEventListener('click', () => {
      const groupId = item.dataset.groupId;
      const groupName = item.dataset.groupName;
      window.currentGroupChat = true;
      openGroupChat(groupId, groupName);
      window.closeSubpage();
    });
  });
}

// 导出全局
window.openNewAgentPage = openNewAgentPage;
window.openGroupChatList = openGroupChatList;