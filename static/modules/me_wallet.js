// static/modules/me_wallet.js
import { api } from './api.js';
import { t } from './me_i18n.js';

// ==================== 积分中心 ====================
export async function openWallet() {
  let balance = 0;
  let computeBalance = 0;
  let historyHtml = '';

  try {
    const balanceData = await api.getBalance();
    balance = balanceData.balance;
  } catch (e) {}

  try {
    const computeData = await api.getComputeBalance();
    computeBalance = computeData.balance || 0;
  } catch (e) {}

  try {
    const historyData = await api.getCreditHistory(20);
    const history = historyData.history || [];
    if (history.length === 0) {
      historyHtml = `<div class="subpage-placeholder">${t('no_history')}</div>`;
    } else {
      historyHtml = '<div class="me-menu">';
      history.forEach(item => {
        const date = new Date(item.created_at).toLocaleString('zh-CN');
        historyHtml += `<div class="me-menu-item"><span class="menu-label">${item.action || t('wallet')}</span><span class="menu-value">${item.points > 0 ? '+' : ''}${item.points}</span></div><div style="padding:0 12px 8px;font-size:12px;color:#999;">${date}</div>`;
      });
      historyHtml += '</div>';
    }
  } catch (e) {
    historyHtml = `<div class="subpage-placeholder">${t('loading_failed') || '加载失败'}</div>`;
  }

  const contentHtml = `
    <div class="wallet-card" style="background: linear-gradient(135deg, #007aff, #00c6ff);">
      <div class="wallet-label">${t('seed_credits')}</div>
      <div class="wallet-balance">${balance}</div>
    </div>
    <div class="wallet-card" style="background: linear-gradient(135deg, #667eea, #764ba2);cursor:pointer;" id="wallet-compute-entry">
      <div class="wallet-label">${t('compute_power')}</div>
      <div class="wallet-balance">${computeBalance}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:4px;">点击进入算力钱包 ›</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="menu-exchange"><span class="menu-label">${t('exchange')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="menu-stake"><span class="menu-label">${t('stake')}</span><span class="menu-arrow">›</span></div>
    </div>
    <div class="section-title">${t('recent_records')}</div>
    ${historyHtml}
  `;
  window.openSubpage(t('wallet'), contentHtml);

  setTimeout(() => {
    document.getElementById('menu-exchange').onclick = openExchangePage;
    document.getElementById('menu-stake').onclick = openStakePage;

    const computeEntry = document.getElementById('wallet-compute-entry');
    if (computeEntry) {
      computeEntry.onclick = () => {
        if (typeof window.openComputeWallet === 'function') {
          window.openComputeWallet(() => openWallet());
        }
      };
    }
  }, 100);
}

function openExchangePage() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">${t('exchange')}</span>
        <input type="number" id="exchange-credits" class="inline-input" placeholder="${t('enter_valid')}">
      </div>
    </div>
    <button class="save-btn" id="save-exchange">${t('confirm')}</button>
  `;
  window.openSubpage(t('exchange'), contentHtml);
  setTimeout(() => {
    document.getElementById('save-exchange').onclick = async () => {
      const credits = parseFloat(document.getElementById('exchange-credits').value);
      if (!credits || credits <= 0) { alert(t('enter_valid')); return; }
      try {
        const data = await api.exchangeCredits(credits);
        const currentPower = parseFloat(localStorage.getItem('sases_compute_power') || '0');
        localStorage.setItem('sases_compute_power', (currentPower + data.compute_power).toString());
        alert(`${t('exchange_success')}! ${data.compute_power}`);
        window.closeSubpage();
        openWallet();
      } catch (e) {
        alert(t('exchange_failed') + ': ' + e.message);
      }
    };
  }, 100);
}

function openStakePage() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">${t('stake')}</span>
        <input type="number" id="stake-credits" class="inline-input" placeholder="${t('enter_valid')}">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">${t('stake_days')}</span>
        <input type="number" id="stake-days" class="inline-input" value="30">
      </div>
    </div>
    <button class="save-btn" id="save-stake">${t('confirm')}</button>
  `;
  window.openSubpage(t('stake'), contentHtml);
  setTimeout(() => {
    document.getElementById('save-stake').onclick = async () => {
      const credits = parseFloat(document.getElementById('stake-credits').value);
      const days = parseInt(document.getElementById('stake-days').value);
      if (!credits || credits <= 0 || !days || days <= 0) { alert(t('enter_valid')); return; }
      try {
        const data = await api.stakeCredits(credits, days);
        alert(`${t('stake_success')}! ${data.expected_reward.toFixed(2)}`);
        window.closeSubpage();
        openWallet();
      } catch (e) {
        alert(t('stake_failed') + ': ' + e.message);
      }
    };
  }, 100);
}

// 挂载到全局
window.openWallet = openWallet;