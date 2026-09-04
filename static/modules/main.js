// static/modules/main.js
import { login, register, isLoggedIn } from './auth.js';
import { api } from './api.js';
import { initMessages } from './messages.js';
import { initChat, openChatWindow, closeChatWindow } from './chat.js';
import { initContacts } from './contacts.js';
import { initDiscover } from './discover.js';
import { initMe } from './me.js';
import { openGroupChat, closeGroupChat } from './group_chat.js';
import { openGlobalSearch } from './search.js';
import { initSideDrawer } from './sidebar.js';
import { showPlusMenu } from './plus_menu.js';
import { t, setLang, getLang } from './i18n.js';

document.addEventListener('DOMContentLoaded', () => {
  window.currentGroupChat = false;
  applyLanguage();
  initLoginUI();
  initBottomNav();
  initTopActions();
  initChat();
  initSideDrawer();
  checkAuthState();
});

function applyLanguage() {
  const lang = getLang();

  // 设置登录界面
  document.getElementById('login-title').textContent = t('login_title');
  document.getElementById('login-subtitle').textContent = t('login_subtitle');
  document.getElementById('login-username').placeholder = t('login_username_placeholder');
  document.getElementById('login-password').placeholder = t('login_password_placeholder');
  document.getElementById('login-btn').textContent = t('login_button');
  document.getElementById('go-register').textContent = t('register_link');
  document.getElementById('forgot-password').textContent = t('forgot_password');

  // 设置底部导航
  document.querySelectorAll('.nav-btn').forEach(btn => {
    const view = btn.dataset.view;
    if (view === 'messages') btn.textContent = t('nav_messages');
    else if (view === 'contacts') btn.textContent = t('nav_contacts');
    else if (view === 'discover') btn.textContent = t('nav_discover');
    else if (view === 'me') btn.textContent = t('nav_me');
  });

  // 设置当前顶部标题
  const activeView = document.querySelector('.nav-btn.active')?.dataset.view;
  if (activeView) {
    const titles = {
      messages: t('nav_messages'),
      contacts: t('nav_contacts'),
      discover: t('nav_discover'),
      me: t('nav_me')
    };
    document.getElementById('top-title').textContent = titles[activeView] || 'SASES';
  }

  // 更新侧边栏菜单项文本
  updateSidebarLanguage();
}

function updateSidebarLanguage() {
  const harnessLabel = document.getElementById('label-harness');
  if (harnessLabel) harnessLabel.textContent = t('harness_tools');
  const pollinationLabel = document.getElementById('label-pollination');
  if (pollinationLabel) pollinationLabel.textContent = t('pollination_switch');
  const marketLabel = document.getElementById('label-market');
  if (marketLabel) marketLabel.textContent = t('market');
  const miniAppsLabel = document.getElementById('label-mini-apps');
  if (miniAppsLabel) miniAppsLabel.textContent = t('mini_apps');
  const drawerTitle = document.getElementById('side-drawer-title');
  if (drawerTitle) drawerTitle.textContent = t('menu');
}

function initLoginUI() {
  const loginBtn = document.getElementById('login-btn');
  const registerLink = document.getElementById('go-register');
  const usernameInput = document.getElementById('login-username');
  const passwordInput = document.getElementById('login-password');
  const agreeCheckbox = document.getElementById('agree-checkbox');
  const langButtons = document.querySelectorAll('.lang-btn');

  if (!loginBtn || !usernameInput || !passwordInput || !registerLink || !agreeCheckbox) return;

  langButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const lang = btn.dataset.lang;
      setLang(lang);
      applyLanguage();
      langButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

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

  const titles = {
    messages: t('nav_messages'),
    contacts: t('nav_contacts'),
    discover: t('nav_discover'),
    me: t('nav_me')
  };
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