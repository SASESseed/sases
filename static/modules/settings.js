// static/modules/settings.js
import { api } from './api.js';
import { t, getLang } from './i18n.js';

export function openSettings() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item" id="set-account"><span class="menu-label">${t('account_security')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-pollination"><span class="menu-label">${t('pollination_plan')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-notify"><span class="menu-label">${t('notification_settings')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-privacy"><span class="menu-label">${t('privacy')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-language"><span class="menu-label">${t('language_settings')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-about"><span class="menu-label">${t('about_sases')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-logout" style="justify-content:center;">
        <span class="menu-label" style="color:#ff3b30;">${t('logout')}</span>
      </div>
    </div>
  `;
  window.openSubpage(t('settings'), contentHtml);

  setTimeout(() => {
    document.getElementById('set-account').addEventListener('click', openAccountSettings);
    document.getElementById('set-pollination').addEventListener('click', openPollinationPlan);
    document.getElementById('set-notify').addEventListener('click', openNotificationSettings);
    document.getElementById('set-privacy').addEventListener('click', openPrivacySettings);
    document.getElementById('set-language').addEventListener('click', openLanguageSettings);
    document.getElementById('set-about').addEventListener('click', openAboutPage);
    document.getElementById('set-logout').addEventListener('click', () => {
      localStorage.removeItem('sases_token');
      localStorage.removeItem('sases_username');
      localStorage.removeItem('sases_user_id');
      localStorage.removeItem('sases_sas_id');
      localStorage.removeItem('sases_credits_cache');
      window.location.reload();
    });
  }, 100);
}

function openPollinationPlan() {
  const contentHtml = `
    <div style="padding:20px 16px;background:#fff;border-radius:8px;margin-bottom:12px;">
      <h3 style="margin-bottom:8px;">🌱 ${t('pollination_plan')}</h3>
      <p style="color:#666;font-size:14px;line-height:1.6;">${getLang() === 'zh' ? '授粉是分享知识、获取积分的重要方式。当你贡献有价值的种子或数据时，你将获得积分奖励。' : 'Pollination is an important way to share knowledge and earn credits. When you contribute valuable seeds or data, you will be rewarded.'}</p>
    </div>
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">${t('basic_value')}</span><span class="menu-value">+1 ${t('credits')}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('professional_value')}</span><span class="menu-value">+2 ${t('credits')}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('extreme_value')}</span><span class="menu-value">+3 ${t('credits')}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('local_model_bonus')}</span><span class="menu-value">${t('extra')} +2 ${t('credits')}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('daily_personal_limit')}</span><span class="menu-value">100 ${t('credits')}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('bad_fruit_reward')}</span><span class="menu-value">+5 ${t('credits')}/${t('times')} (${t('daily_limit')}50)</span></div>
    </div>
    <div style="margin-top:12px;background:#f5f5f5;border-radius:8px;padding:12px;font-size:13px;color:#888;">
      ${getLang() === 'zh' ? '群任务授粉分配：群主5%，算力提供者70%，执行者15%，红包池10%。具体规则以群设置为准。' : 'Group task pollination distribution: owner 5%, compute providers 70%, executors 15%, red packet pool 10%. Specific rules are based on group settings.'}
    </div>
  `;
  window.openSubpage(t('pollination_plan'), contentHtml, { showMore: false });
}

function openAccountSettings() {
  const username = localStorage.getItem('sases_username') || '用户';
  const sasesId = localStorage.getItem('sases_sas_id') || '未设置';
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">${t('username')}</span><span class="menu-value">${username}</span></div>
      <div class="me-menu-item"><span class="menu-label">SASES ID</span><span class="menu-value">${sasesId}</span></div>
      <div class="me-menu-item" id="account-change-password"><span class="menu-label">${t('change_password')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="account-logout-devices"><span class="menu-label">${t('device_management')}</span><span class="menu-arrow">›</span></div>
    </div>
  `;
  window.openSubpage(t('account_security'), contentHtml);
  setTimeout(() => {
    document.getElementById('account-change-password').addEventListener('click', () => alert('修改密码功能待实现'));
    document.getElementById('account-logout-devices').addEventListener('click', () => alert('登录设备管理待实现'));
  }, 100);
}

function openNotificationSettings() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">${t('receive_new_message')}</span><label class="switch"><input type="checkbox" checked><span class="slider"></span></label></div>
      <div class="me-menu-item"><span class="menu-label">${t('agent_dynamic')}</span><label class="switch"><input type="checkbox" checked><span class="slider"></span></label></div>
      <div class="me-menu-item"><span class="menu-label">${t('credit_change')}</span><label class="switch"><input type="checkbox" checked><span class="slider"></span></label></div>
      <div class="me-menu-item"><span class="menu-label">${t('bounty_task')}</span><label class="switch"><input type="checkbox"><span class="slider"></span></label></div>
    </div>
  `;
  window.openSubpage(t('notification_settings'), contentHtml);
}

function openPrivacySettings() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">${t('who_can_see_agents')}</span><span class="menu-value">${t('friends_only')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('who_can_search_me')}</span><span class="menu-value">${t('everyone')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="privacy-export-data"><span class="menu-label">${t('export_data')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="privacy-delete-data"><span class="menu-label">${t('delete_cloud_data')}</span><span class="menu-arrow">›</span></div>
    </div>
  `;
  window.openSubpage(t('privacy'), contentHtml);
  setTimeout(() => {
    document.getElementById('privacy-export-data').addEventListener('click', async () => {
      try {
        const data = await api.exportUserData();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'sases_data.json';
        a.click();
        URL.revokeObjectURL(url);
        alert('导出成功，文件已下载');
      } catch (e) {
        alert('导出失败：' + e.message);
      }
    });
    document.getElementById('privacy-delete-data').addEventListener('click', async () => {
      if (!confirm('确定要删除您的云端公开数据吗？此操作不可恢复。')) return;
      try {
        await api.deleteUserCloudData();
        alert('已删除云端数据');
      } catch (e) {
        alert('删除失败：' + e.message);
      }
    });
  }, 100);
}

function openLanguageSettings() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item" id="lang-zh"><span class="menu-label">简体中文</span><span class="menu-check">✓</span></div>
      <div class="me-menu-item" id="lang-en"><span class="menu-label">English</span><span class="menu-check"></span></div>
    </div>
  `;
  window.openSubpage(t('language_settings'), contentHtml);
  setTimeout(() => {
    document.getElementById('lang-zh').addEventListener('click', () => {
      setLang('zh');
      alert('已切换为简体中文');
      window.closeSubpage();
      openSettings();
    });
    document.getElementById('lang-en').addEventListener('click', () => {
      setLang('en');
      alert('Switched to English');
      window.closeSubpage();
      openSettings();
    });
  }, 100);
}

function openAboutPage() {
  const contentHtml = `
    <div style="text-align:center;padding:30px 20px;">
      <div style="font-size:40px;margin-bottom:16px;">🌱</div>
      <div style="font-size:20px;font-weight:600;">SASES</div>
      <div style="color:#888;font-size:14px;margin-top:8px;">${getLang() === 'zh' ? '版本 v0.12.1' : 'Version v0.12.1'}</div>
      <div style="color:#888;font-size:13px;margin-top:4px;">${getLang() === 'zh' ? '隐私优先的自进化 AI 生态' : 'Privacy-first self-evolving AI ecosystem'}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="about-docs"><span class="menu-label">${t('developer_docs')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="about-license"><span class="menu-label">${t('open_source_license')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="about-feedback"><span class="menu-label">${t('feedback')}</span><span class="menu-arrow">›</span></div>
    </div>
  `;
  window.openSubpage(t('about_sases'), contentHtml);
  setTimeout(() => {
    document.getElementById('about-docs').addEventListener('click', () => window.openSubpage(t('developer_docs'), '<div class="subpage-placeholder">文档待补充</div>'));
    document.getElementById('about-license').addEventListener('click', () => window.openSubpage(t('open_source_license'), '<div class="subpage-placeholder">MIT License</div>'));
    document.getElementById('about-feedback').addEventListener('click', () => window.openSubpage(t('feedback'), '<div class="subpage-placeholder">反馈渠道待实现</div>'));
  }, 100);
}