// static/modules/me.js
import { api } from './api.js';
import { t } from './me_i18n.js';

let initialized = false;

export function initMe() {
  if (initialized) return;
  initialized = true;

  const container = document.getElementById('me-content');
  if (!container) return;

  const username = localStorage.getItem('sases_username') || '用户';
  const sasesId = localStorage.getItem('sases_sas_id') || t('not_set');
  const credits = localStorage.getItem('sases_credits_cache') || '0';

  container.innerHTML = `
    <div class="me-profile-card">
      <div class="me-profile-main" id="me-profile-main">
        <div class="me-avatar">${username.charAt(0).toUpperCase()}</div>
        <div class="me-info">
          <div class="me-name">${username}</div>
          <div class="me-id">${t('sases_id')}: ${sasesId}</div>
          <div class="me-credits">${t('seed_credits')}: ${credits}</div>
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
        <span class="menu-label">${t('wallet')}</span>
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
        <div style="font-size:16px;margin-bottom:20px;">${t('scan_add_friend')}</div>
        <div style="width:200px;height:200px;margin:0 auto;background:#fff;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:80px;">🔳</div>
        <div style="margin-top:16px;color:#888;font-size:13px;">${t('sases_id')}: ${sasesId}</div>
      </div>
    `);
  });

  document.getElementById('menu-models').addEventListener('click', () => {
    if (typeof window.openModelManagement === 'function') window.openModelManagement();
    else alert(t('model_management') + ' - ' + t('coming_soon'));
  });
  document.getElementById('menu-wallet').addEventListener('click', () => {
    if (typeof window.openWallet === 'function') window.openWallet();
    else alert(t('wallet') + ' - ' + t('coming_soon'));
  });
  document.getElementById('menu-knowledge').addEventListener('click', openKnowledgeBase);
  document.getElementById('menu-contributions').addEventListener('click', openContributions);
  document.getElementById('menu-settings').addEventListener('click', () => {
    if (typeof window.openSettings === 'function') window.openSettings();
    else alert(t('settings') + ' - ' + t('coming_soon'));
  });

  api.getBalance().then(data => {
    localStorage.setItem('sases_credits_cache', data.balance);
    const creditEl = document.querySelector('.me-credits');
    if (creditEl) creditEl.textContent = `${t('seed_credits')}: ${data.balance}`;
  }).catch(() => {});
}

// ==================== 个人资料 ====================
async function openPersonalInfo() {
  let profile = null;
  try {
    profile = await api.getUserProfile();
  } catch (e) {
    console.warn('获取资料失败', e);
  }

  const username = profile?.username || localStorage.getItem('sases_username') || '用户';
  const sasesId = profile?.sases_id || localStorage.getItem('sases_sas_id') || t('not_set');
  const gender = profile?.gender || localStorage.getItem('sases_gender') || t('not_set');
  const region = profile?.region || localStorage.getItem('sases_region') || t('not_set');
  const signature = profile?.signature || localStorage.getItem('sases_signature') || t('not_set');

  const contentHtml = `
    <div class="personal-info-header">
      <div class="personal-info-avatar">${username.charAt(0).toUpperCase()}</div>
      <div class="personal-info-name">${username}</div>
      <div class="personal-info-id">${t('sases_id')}: ${sasesId}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="edit-nickname">
        <span class="menu-label">${t('nickname')}</span>
        <span class="menu-value">${username}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="edit-sases-id">
        <span class="menu-label">${t('sases_id')}</span>
        <span class="menu-value">${sasesId}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="edit-gender">
        <span class="menu-label">${t('gender')}</span>
        <span class="menu-value">${gender}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="edit-region">
        <span class="menu-label">${t('region')}</span>
        <span class="menu-value">${region}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="edit-signature">
        <span class="menu-label">${t('signature')}</span>
        <span class="menu-value">${signature}</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
  `;
  window.openSubpage(t('personal_info'), contentHtml);

  setTimeout(() => {
    document.getElementById('edit-nickname').onclick = async () => {
      const newName = prompt(t('nickname') + ':', username);
      if (newName && newName.trim()) {
        try {
          await api.updateUserProfile({ username: newName.trim() });
          localStorage.setItem('sases_username', newName.trim());
          alert(t('update_success'));
          window.closeSubpage();
          initMe();
        } catch (e) { alert(t('update_failed') + ': ' + e.message); }
      }
    };
    document.getElementById('edit-sases-id').onclick = () => alert(t('sases_id') + ' ' + t('not_set'));
    document.getElementById('edit-gender').onclick = async () => {
      const newGender = prompt(t('gender') + ':', gender);
      if (newGender) {
        try {
          await api.updateUserProfile({ gender: newGender });
          localStorage.setItem('sases_gender', newGender);
          alert(t('update_success'));
          window.closeSubpage();
          openPersonalInfo();
        } catch (e) { alert(t('update_failed') + ': ' + e.message); }
      }
    };
    document.getElementById('edit-region').onclick = async () => {
      const newRegion = prompt(t('region') + ':', region);
      if (newRegion) {
        try {
          await api.updateUserProfile({ region: newRegion });
          localStorage.setItem('sases_region', newRegion);
          alert(t('update_success'));
          window.closeSubpage();
          openPersonalInfo();
        } catch (e) { alert(t('update_failed') + ': ' + e.message); }
      }
    };
    document.getElementById('edit-signature').onclick = async () => {
      const newSignature = prompt(t('signature') + ':', signature);
      if (newSignature) {
        try {
          await api.updateUserProfile({ signature: newSignature });
          localStorage.setItem('sases_signature', newSignature);
          alert(t('update_success'));
          window.closeSubpage();
          openPersonalInfo();
        } catch (e) { alert(t('update_failed') + ': ' + e.message); }
      }
    };
  }, 100);
}

// ==================== 知识库 ====================
async function openKnowledgeBase() {
  let knowledgeHtml = '';
  try {
    const data = await api.listKnowledge();
    const knowledge = data.knowledge || [];
    if (knowledge.length === 0) knowledgeHtml = `<div class="subpage-placeholder">${t('no_knowledge')}</div>`;
    else {
      knowledgeHtml = '<div class="me-menu">';
      knowledge.forEach(item => {
        const verifiedIcon = item.verified ? '✅' : '❌';
        knowledgeHtml += `<div class="me-menu-item"><span class="menu-icon">${verifiedIcon}</span><div class="menu-text"><div class="menu-title">${item.task}</div><div class="menu-desc">${item.solution.substring(0, 50)}...</div></div></div>`;
      });
      knowledgeHtml += '</div>';
    }
  } catch (e) { knowledgeHtml = `<div class="subpage-placeholder">${t('loading_failed')}</div>`; }
  window.openSubpage(t('knowledge_base'), knowledgeHtml);
}

// ==================== 我的贡献 ====================
async function openContributions() {
  let contribHtml = '';
  try {
    const data = await api.getCreditHistory(50);
    const history = data.history || [];
    if (history.length === 0) contribHtml = `<div class="subpage-placeholder">${t('no_history')}</div>`;
    else {
      contribHtml = '<div class="me-menu">';
      history.forEach(item => {
        const date = new Date(item.created_at).toLocaleString('zh-CN');
        contribHtml += `<div class="me-menu-item"><span class="menu-label">${item.action || t('my_contributions')}</span><span class="menu-value">${item.points > 0 ? '+' : ''}${item.points}</span></div><div style="padding:0 12px 8px;font-size:12px;color:#999;">${date} · ${item.detail || ''}</div>`;
      });
      contribHtml += '</div>';
    }
  } catch (e) { contribHtml = `<div class="subpage-placeholder">${t('loading_failed')}</div>`; }
  window.openSubpage(t('my_contributions'), contribHtml);
}

// 导出全局（供其他模块调用或挂载）
window.openKnowledgeBase = openKnowledgeBase;
window.openContributions = openContributions;