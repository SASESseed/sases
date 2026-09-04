// static/modules/me.js
import { api } from './api.js';
import { t, getLang } from './i18n.js';
import { openPersonalInfo } from './me_profile.js';
import { openModelManagement } from './model_management.js';
import { openWallet } from './wallet.js';
import { openKnowledgeBase } from './knowledge.js';
import { openContributions } from './contributions.js';
import { openSettings } from './settings.js';

let initialized = false;

export function initMe() {
  if (initialized) return;
  initialized = true;

  const container = document.getElementById('me-content');
  if (!container) return;

  const username = localStorage.getItem('sases_username') || '用户';
  const sasesId = localStorage.getItem('sases_sas_id') || '未设置';
  const credits = localStorage.getItem('sases_credits_cache') || '0';

  container.innerHTML = `
    <div class="me-profile-card">
      <div class="me-profile-main" id="me-profile-main">
        <div class="me-avatar">${username.charAt(0).toUpperCase()}</div>
        <div class="me-info">
          <div class="me-name">${username}</div>
          <div class="me-id">SASES ID: ${sasesId}</div>
          <div class="me-credits">${t('credits_cache')} ${credits}</div>
        </div>
        <div class="me-qrcode" id="me-qrcode">${t('qr_code')}</div>
        <div class="me-edit" id="me-edit-profile">✏️</div>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="menu-models">
        <span class="menu-icon">🤖</span>
        <span class="menu-label">${t('model_management')}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="menu-wallet">
        <span class="menu-icon">💰</span>
        <span class="menu-label">${t('credits_center')}</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="menu-knowledge">
        <span class="menu-icon">📚</span>
        <span class="menu-label">${t('knowledge_base')}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="menu-contributions">
        <span class="menu-icon">🌱</span>
        <span class="menu-label">${t('my_contributions')}</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="menu-settings">
        <span class="menu-icon">⚙️</span>
        <span class="menu-label">${t('settings')}</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
  `;

  document.getElementById('me-profile-main').addEventListener('click', openPersonalInfo);
  document.getElementById('me-edit-profile').addEventListener('click', (e) => {
    e.stopPropagation();
    openPersonalInfo();
  });

  document.getElementById('me-qrcode').addEventListener('click', (e) => {
    e.stopPropagation();
    window.openSubpage(t('qr_code'), `
      <div style="text-align:center;padding:40px 20px;">
        <div style="font-size:16px;margin-bottom:20px;">${t('qr_code')}</div>
        <div style="width:200px;height:200px;margin:0 auto;background:#fff;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:80px;">🔳</div>
        <div style="margin-top:16px;color:#888;font-size:13px;">SASES ID: ${sasesId}</div>
      </div>
    `);
  });

  document.getElementById('menu-models').addEventListener('click', openModelManagement);
  document.getElementById('menu-wallet').addEventListener('click', openWallet);
  document.getElementById('menu-knowledge').addEventListener('click', openKnowledgeBase);
  document.getElementById('menu-contributions').addEventListener('click', openContributions);
  document.getElementById('menu-settings').addEventListener('click', openSettings);

  // 更新缓存积分
  api.getBalance().then(data => {
    localStorage.setItem('sases_credits_cache', data.balance);
    const creditEl = document.querySelector('.me-credits');
    if (creditEl) creditEl.textContent = `${t('credits_cache')} ${data.balance}`;
  }).catch(() => {});
}