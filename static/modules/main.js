// static/modules/main.js
import { login, register, isLoggedIn } from './auth.js';
import { api } from './api.js';
import { initMessages } from './messages.js';
import { initChat, openChatWindow, closeChatWindow } from './chat.js';
import { initContacts } from './contacts.js';
import { initDiscover } from './discover.js';
import { initMe } from './me.js';
import { openGroupChat, closeGroupChat } from './group_chat.js';

document.addEventListener('DOMContentLoaded', () => {
  window.currentGroupChat = false;
  initLoginUI();
  initBottomNav();
  initTopActions();
  initChat();
  initSideDrawer();
  checkAuthState();
});

function initLoginUI() {
  const loginBtn = document.getElementById('login-btn');
  const registerLink = document.getElementById('go-register');
  const usernameInput = document.getElementById('login-username');
  const passwordInput = document.getElementById('login-password');
  const agreeCheckbox = document.getElementById('agree-checkbox');
  const loginTitle = document.getElementById('login-title');
  const loginSubtitle = document.getElementById('login-subtitle');
  const langButtons = document.querySelectorAll('.lang-btn');

  if (!loginBtn || !usernameInput || !passwordInput || !registerLink || !agreeCheckbox) return;

  langButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const lang = btn.dataset.lang;
      langButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyLanguage(lang);
    });
  });

  function applyLanguage(lang) {
    if (lang === 'en') {
      loginTitle.textContent = 'SASES';
      loginSubtitle.textContent = 'Login to your account';
      loginBtn.textContent = 'Login';
      registerLink.textContent = 'Register';
    } else {
      loginTitle.textContent = 'SASES';
      loginSubtitle.textContent = '登录你的账号';
      loginBtn.textContent = '登录';
      registerLink.textContent = '注册新账号';
    }
  }

  registerLink.addEventListener('click', (e) => {
    e.preventDefault();
    alert('注册功能请点击登录按钮下方链接');
  });

  loginBtn.addEventListener('click', async () => {
    if (!agreeCheckbox.checked) {
      alert('请先阅读并同意用户协议和隐私政策');
      return;
    }
    const username = usernameInput.value.trim();
    const password = passwordInput.value;
    if (!username || !password) {
      alert('请输入用户名和密码');
      return;
    }
    try {
      await login(username, password);
      enterMainApp();
    } catch (e) {
      alert('登录失败：' + e.message);
    }
  });

  passwordInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') loginBtn.click();
  });
}

function checkAuthState() {
  if (isLoggedIn()) {
    enterMainApp();
  } else {
    showLogin();
  }
}

function showLogin() {
  document.getElementById('view-login').style.display = 'flex';
  document.getElementById('main-app').style.display = 'none';
}

function enterMainApp() {
  document.getElementById('view-login').style.display = 'none';
  document.getElementById('main-app').style.display = 'flex';
  activateMainView('messages');
}

function activateMainView(viewName) {
  closeChatWindow();
  closeSubpage();

  document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.view === viewName));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  const target = document.getElementById(`view-${viewName}`);
  if (target) target.classList.add('active');

  const titles = { messages: '消息', contacts: '智能体', discover: '发现', me: '我的' };
  document.getElementById('top-title').textContent = titles[viewName] || 'SASES';

  const topLeft = document.getElementById('top-left');
  if (topLeft) {
    topLeft.style.display = viewName === 'messages' ? 'flex' : 'none';
  }

  const showActions = viewName !== 'me';
  document.getElementById('top-actions').style.display = showActions ? 'flex' : 'none';

  if (viewName === 'messages') initMessages();
  if (viewName === 'contacts') initContacts();
  if (viewName === 'discover') initDiscover();
  if (viewName === 'me') initMe();
}

function initBottomNav() {
  const nav = document.querySelector('.bottom-nav');
  if (!nav) return;
  nav.addEventListener('click', (e) => {
    const btn = e.target.closest('.nav-btn');
    if (!btn) return;
    activateMainView(btn.dataset.view);
  });
}

function initTopActions() {
  const searchBtn = document.getElementById('top-search-btn');
  const plusBtn = document.getElementById('top-plus-btn');
  if (searchBtn) searchBtn.addEventListener('click', openGlobalSearch);
  if (plusBtn) plusBtn.addEventListener('click', showPlusMenu);
}

// ==================== 全局搜索 ====================
async function openGlobalSearch() {
  const contentHtml = `
    <div class="subpage-search-bar">
      <input type="text" class="search-input" id="global-search-input" placeholder="搜索用户/智能体/知识">
      <button class="search-btn" id="global-search-btn">搜索</button>
    </div>
    <div id="global-search-results"></div>
  `;
  window.openSubpage('搜索', contentHtml);

  setTimeout(() => {
    const searchBtn = document.getElementById('global-search-btn');
    const searchInput = document.getElementById('global-search-input');
    if (!searchBtn || !searchInput) return;

    searchBtn.addEventListener('click', () => {
      const q = searchInput.value.trim();
      if (q) performGlobalSearch(q);
    });
    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        const q = searchInput.value.trim();
        if (q) performGlobalSearch(q);
      }
    });
  }, 100);
}

async function performGlobalSearch(q) {
  const resultsContainer = document.getElementById('global-search-results');
  if (!resultsContainer) return;
  resultsContainer.innerHTML = '<div class="subpage-placeholder">搜索中...</div>';
  try {
    const data = await api.globalSearch(q);
    renderSearchResults(data);
  } catch (e) {
    resultsContainer.innerHTML = `<div class="subpage-placeholder">搜索失败：${e.message}</div>`;
  }
}

function renderSearchResults(data) {
  const container = document.getElementById('global-search-results');
  if (!container) return;
  let html = '';

  if (data.users && data.users.length > 0) {
    html += '<div class="section-title">用户</div><div class="me-menu">';
    data.users.forEach(user => {
      html += `
        <div class="me-menu-item">
          <span class="menu-icon">👤</span>
          <div class="menu-text">
            <div class="menu-title">${user.username}</div>
            <div class="menu-desc">${user.sases_id || ''}</div>
          </div>
        </div>
      `;
    });
    html += '</div>';
  }

  if (data.agents && data.agents.length > 0) {
    html += '<div class="section-title">智能体</div><div class="me-menu">';
    data.agents.forEach(agent => {
      html += `
        <div class="me-menu-item">
          <span class="menu-icon">🤖</span>
          <div class="menu-text">
            <div class="menu-title">${agent.name}</div>
            <div class="menu-desc">${agent.owner_name} · ${agent.provider || agent.model_name}</div>
          </div>
        </div>
      `;
    });
    html += '</div>';
  }

  if (data.knowledge && data.knowledge.length > 0) {
    html += '<div class="section-title">知识库</div><div class="me-menu">';
    data.knowledge.forEach(item => {
      html += `
        <div class="me-menu-item">
          <span class="menu-icon">📚</span>
          <div class="menu-text">
            <div class="menu-title">${item.task}</div>
            <div class="menu-desc">${item.solution.substring(0, 50)}...</div>
          </div>
        </div>
      `;
    });
    html += '</div>';
  }

  if (!html) {
    html = '<div class="subpage-placeholder">无结果</div>';
  }
  container.innerHTML = html;
}

// ==================== 侧边栏 ====================
function initSideDrawer() {
  const hamburgerBtn = document.getElementById('hamburger-btn');
  const drawer = document.getElementById('side-drawer');
  const overlay = document.getElementById('side-drawer-overlay');
  if (!hamburgerBtn || !drawer || !overlay) return;

  hamburgerBtn.addEventListener('click', () => {
    drawer.style.display = 'block';
    setTimeout(() => drawer.classList.add('open'), 10);
  });

  overlay.addEventListener('click', () => {
    drawer.classList.remove('open');
    setTimeout(() => drawer.style.display = 'none', 300);
  });

  const menuHarness = document.getElementById('menu-harness');
  const menuMarket = document.getElementById('menu-market');
  const menuMiniApps = document.getElementById('menu-mini-apps');
  const pollinationToggle = document.getElementById('pollination-toggle');

  if (menuHarness) {
    menuHarness.addEventListener('click', () => {
      closeSideDrawer();
      window.openSubpage('Harness 工具', '<div class="subpage-placeholder">Harness 工具加载中...</div>');
      loadHarnessTools();
    });
  }
  if (menuMarket) {
    menuMarket.addEventListener('click', () => {
      closeSideDrawer();
      openMarketPage();
    });
  }
  if (menuMiniApps) {
    menuMiniApps.addEventListener('click', () => {
      closeSideDrawer();
      window.openSubpage('小程序', '<div class="subpage-placeholder">小程序待实现</div>');
    });
  }
  if (pollinationToggle) {
    const savedState = localStorage.getItem('sases_pollination_enabled');
    if (savedState !== null) pollinationToggle.checked = savedState === 'true';
    pollinationToggle.addEventListener('change', () => {
      localStorage.setItem('sases_pollination_enabled', pollinationToggle.checked);
      alert('授粉功能已' + (pollinationToggle.checked ? '开启' : '关闭'));
    });
  }
}

function closeSideDrawer() {
  const drawer = document.getElementById('side-drawer');
  if (drawer) {
    drawer.classList.remove('open');
    setTimeout(() => drawer.style.display = 'none', 300);
  }
}

async function loadHarnessTools() {
  try {
    const data = await api.getHarnessModules();
    const modules = data.modules || [];
    let html = '';
    if (modules.length === 0) {
      html = '<div class="subpage-placeholder">暂无模块</div>';
    } else {
      html = '<div class="me-menu">';
      modules.forEach(mod => {
        html += `
          <div class="me-menu-item">
            <span class="menu-icon">🔧</span>
            <div class="menu-text">
              <div class="menu-title">${mod.name}</div>
              <div class="menu-desc">${mod.description || mod.id}</div>
            </div>
          </div>
        `;
      });
      html += '</div>';
    }
    document.getElementById('subpage-content').innerHTML = html;
  } catch (e) {
    document.getElementById('subpage-content').innerHTML = '<div class="subpage-placeholder">加载失败</div>';
  }
}

// ==================== 右上角加号菜单 ====================
function showPlusMenu() {
  const view = document.querySelector('.nav-btn.active')?.dataset.view;
  let menuItems = [];

  if (view === 'messages') {
    menuItems = [
      { icon: '👥', label: '发起群聊', action: () => window.openGroupChatList ? window.openGroupChatList() : window.openSubpage('发起群聊', '<div class="subpage-placeholder">功能待实现</div>') },
      { icon: '🧑‍🤝‍🧑', label: '添加智能体', action: () => window.openNewAgentPage ? window.openNewAgentPage() : window.openSubpage('添加智能体', '<div class="subpage-placeholder">功能待实现</div>') },
      { icon: '📷', label: '扫一扫', action: () => window.openSubpage('扫一扫', '<div class="subpage-placeholder">功能待实现</div>') }
    ];
  } else if (view === 'contacts') {
    menuItems = [
      { icon: '🧑‍🤝‍🧑', label: '添加智能体', action: () => window.openNewAgentPage ? window.openNewAgentPage() : window.openSubpage('添加智能体', '<div class="subpage-placeholder">功能待实现</div>') },
      { icon: '👥', label: '创建群聊', action: () => window.openSubpage('创建群聊', '<div class="subpage-placeholder">功能待实现</div>') }
    ];
  } else if (view === 'discover') {
    menuItems = [
      { icon: '📷', label: '扫一扫', action: () => window.openSubpage('扫一扫', '<div class="subpage-placeholder">功能待实现</div>') },
      { icon: '🔄', label: '刷新', action: () => location.reload() }
    ];
  }

  if (menuItems.length === 0) return;

  const menu = document.getElementById('plus-menu');
  const content = menu ? menu.querySelector('.plus-menu-content') : null;
  if (!menu || !content) return;

  let html = '';
  menuItems.forEach(item => {
    html += `
      <div class="plus-menu-item">
        <span class="plus-menu-icon">${item.icon}</span>
        <span class="plus-menu-label">${item.label}</span>
      </div>
    `;
  });
  content.innerHTML = html;
  menu.style.display = 'block';

  content.querySelectorAll('.plus-menu-item').forEach((el, index) => {
    el.addEventListener('click', () => {
      closePlusMenu();
      const item = menuItems[index];
      if (item && item.action) item.action();
    });
  });

  const overlay = document.getElementById('plus-menu-overlay');
  if (overlay) overlay.onclick = closePlusMenu;
}

function closePlusMenu() {
  const menu = document.getElementById('plus-menu');
  if (menu) menu.style.display = 'none';
}

// ==================== 交易市场页面（仅买卖算力） ====================
async function openMarketPage() {
  let ordersHtml = '<div class="subpage-placeholder">加载中...</div>';
  window.openSubpage('交易市场', ordersHtml);

  try {
    const data = await api.listMarketOrders();
    const orders = data.orders || [];
    if (orders.length === 0) {
      ordersHtml = '<div class="subpage-placeholder">暂无订单</div>';
    } else {
      ordersHtml = '<div class="me-menu">';
      orders.forEach(order => {
        const typeLabel = order.order_type === 'buy_compute' ? '买算力' : '卖算力';
        const statusText = order.status === 'open' ? '进行中' : '已完成';
        ordersHtml += `
          <div class="me-menu-item">
            <div class="menu-text">
              <div class="menu-title">${order.description} (${typeLabel})</div>
              <div class="menu-desc">${order.owner_name} · ${order.price}积分 · ${statusText}</div>
            </div>
            ${order.status === 'open' && order.user_id !== parseInt(localStorage.getItem('sases_user_id') || '0') ? `<button class="accept-order-btn" data-order-id="${order.id}">接单</button>` : ''}
          </div>
        `;
      });
      ordersHtml += '</div>';
    }
  } catch (e) {
    ordersHtml = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }

  const contentHtml = `
    <div class="market-publish-area">
      <select id="market-order-type" class="market-input">
        <option value="buy_compute">买算力（用积分购买）</option>
        <option value="sell_compute">卖算力（换取积分）</option>
      </select>
      <input type="number" id="market-amount" class="market-input" placeholder="算力数量（如 100）" min="1">
      <input type="number" id="market-price" class="market-input" placeholder="单价（积分/算力）" min="0.01" step="0.01">
      <div style="font-size:13px;color:#666;">总价：<span id="market-total">0</span> 积分</div>
      <button id="market-publish-btn" class="save-btn">发布订单</button>
    </div>
    ${ordersHtml}
  `;
  document.getElementById('subpage-content').innerHTML = contentHtml;

  const typeSelect = document.getElementById('market-order-type');
  const amountInput = document.getElementById('market-amount');
  const priceInput = document.getElementById('market-price');
  const totalSpan = document.getElementById('market-total');
  const publishBtn = document.getElementById('market-publish-btn');

  function updateTotal() {
    const amount = parseFloat(amountInput.value) || 0;
    const price = parseFloat(priceInput.value) || 0;
    totalSpan.textContent = (amount * price).toFixed(2);
  }
  amountInput.addEventListener('input', updateTotal);
  priceInput.addEventListener('input', updateTotal);

  publishBtn.addEventListener('click', async () => {
    const order_type = typeSelect.value;
    const amount = parseFloat(amountInput.value);
    const price = parseFloat(priceInput.value);
    if (!amount || amount <= 0 || !price || price <= 0) { alert('请填写有效的数量和价格'); return; }
    const description = `${amount} 算力`;
    try {
      await api.createMarketOrder(order_type, description, amount * price);
      alert('发布成功');
      openMarketPage();
    } catch (e) {
      alert('发布失败：' + e.message);
    }
  });

  // 绑定接单
  document.querySelectorAll('.accept-order-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const orderId = btn.dataset.orderId;
      if (!confirm('确认接单？将扣除相应积分。')) return;
      try {
        await api.acceptMarketOrder(orderId);
        alert('接单成功');
        openMarketPage();
      } catch (e) {
        alert('接单失败：' + e.message);
      }
    });
  });
}

// ==================== 二级页面控制 ====================
export function openSubpage(title, contentHtml, options = {}) {
  const subpageTitle = document.getElementById('subpage-title');
  const subpageContent = document.getElementById('subpage-content');
  if (!subpageTitle || !subpageContent) return;

  subpageTitle.textContent = title;
  subpageContent.innerHTML = contentHtml;

  const bottomNav = document.querySelector('.bottom-nav');
  const topBar = document.querySelector('.top-bar');
  if (bottomNav) bottomNav.style.display = 'none';
  if (topBar) topBar.style.display = 'none';

  const avatarEl = document.getElementById('subpage-avatar');
  if (avatarEl) {
    if (options.avatarHtml) {
      avatarEl.innerHTML = options.avatarHtml;
      avatarEl.style.display = 'flex';
    } else {
      avatarEl.style.display = 'none';
    }
  }

  const moreBtn = document.getElementById('subpage-more-btn');
  if (moreBtn) {
    if (options.showMore) {
      moreBtn.style.display = 'block';
      moreBtn.onclick = options.onMore || (() => alert('更多操作待实现'));
    } else {
      moreBtn.style.display = 'none';
      moreBtn.onclick = null;
    }
  }

  // 重新绑定返回按钮
  const backBtn = document.getElementById('subpage-back-btn');
  if (backBtn) {
    backBtn.onclick = closeSubpage;
  }

  const subpage = document.getElementById('view-subpage');
  if (subpage) subpage.style.display = 'flex';
}

export function closeSubpage() {
  const subpage = document.getElementById('view-subpage');
  if (subpage) subpage.style.display = 'none';
  const bottomNav = document.querySelector('.bottom-nav');
  const topBar = document.querySelector('.top-bar');
  if (bottomNav) bottomNav.style.display = 'flex';
  if (topBar) topBar.style.display = 'flex';
}

window.openSubpage = openSubpage;
window.closeSubpage = closeSubpage;