// static/modules/wallet.js
import { api } from './api.js';
import { t } from './i18n.js';

export async function openWallet() {
  let balance = 0;
  let computePower = parseFloat(localStorage.getItem('sases_compute_power') || '0');
  let historyHtml = '';

  try {
    const balanceData = await api.getBalance();
    balance = balanceData.balance;
  } catch (e) {
    console.warn('获取种子积分失败', e);
  }

  try {
    const historyData = await api.getCreditHistory(20);
    const history = historyData.history || [];
    if (history.length === 0) {
      historyHtml = `<div class="subpage-placeholder">${t('no_credit_history')}</div>`;
    } else {
      historyHtml = '<div class="me-menu">';
      history.forEach(item => {
        const date = new Date(item.created_at).toLocaleString('zh-CN');
        historyHtml += `
          <div class="me-menu-item">
            <span class="menu-label">${item.action || '积分变动'}</span>
            <span class="menu-value">${item.points > 0 ? '+' : ''}${item.points} ${t('credits')}</span>
          </div>
          <div style="padding:0 12px 8px;font-size:12px;color:#999;">${date}</div>
        `;
      });
      historyHtml += '</div>';
    }
  } catch (e) {
    historyHtml = `<div class="subpage-placeholder">${t('load_failed')}</div>`;
  }

  const contentHtml = `
    <div class="wallet-card" style="background: linear-gradient(135deg, #007aff, #00c6ff);">
      <div class="wallet-label">${t('balance')}</div>
      <div class="wallet-balance">${balance}</div>
    </div>
    <div class="wallet-card" style="background: linear-gradient(135deg, #34c759, #b2df8a);">
      <div class="wallet-label">${t('compute_power')}</div>
      <div class="wallet-balance">${computePower}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="menu-exchange"><span class="menu-label">${t('exchange_credits')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="menu-stake"><span class="menu-label">${t('stake_credits')}</span><span class="menu-arrow">›</span></div>
    </div>
    <div class="section-title">${t('recent_records')}</div>
    ${historyHtml}
  `;
  window.openSubpage(t('credits_center'), contentHtml);

  setTimeout(() => {
    const exchangeMenu = document.getElementById('menu-exchange');
    const stakeMenu = document.getElementById('menu-stake');
    if (exchangeMenu) exchangeMenu.addEventListener('click', openExchangePage);
    if (stakeMenu) stakeMenu.addEventListener('click', openStakePage);
  }, 100);
}

function openExchangePage() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">${t('credits')}</span>
        <input type="number" id="exchange-credits" class="inline-input" placeholder="${t('input_placeholder')}">
      </div>
    </div>
    <div style="background:#e8f5e9;border-radius:6px;padding:10px;margin-top:12px;font-size:12px;color:#2e7d32;">
      💡 ${t('exchange_rule')}
    </div>
    <button class="save-btn" id="save-exchange">${t('confirm_exchange')}</button>
  `;
  window.openSubpage(t('exchange_credits'), contentHtml);
  setTimeout(() => {
    document.getElementById('save-exchange').addEventListener('click', async () => {
      const credits = parseFloat(document.getElementById('exchange-credits').value);
      if (!credits || credits <= 0) { alert(t('please_input_all')); return; }
      try {
        const data = await api.exchangeCredits(credits);
        const currentPower = parseFloat(localStorage.getItem('sases_compute_power') || '0');
        localStorage.setItem('sases_compute_power', (currentPower + data.compute_power).toString());
        alert(`${t('add_success')} ${data.compute_power} ${t('compute_power')}`);
        window.closeSubpage();
        openWallet();
      } catch (e) {
        alert(t('add_failed') + ': ' + e.message);
      }
    });
  }, 100);
}

function openStakePage() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">${t('credits')}</span>
        <input type="number" id="stake-credits" class="inline-input" placeholder="${t('input_placeholder')}">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">${t('stake_days')}</span>
        <input type="number" id="stake-days" class="inline-input" value="30">
      </div>
    </div>
    <button class="save-btn" id="save-stake">${t('confirm_stake')}</button>
  `;
  window.openSubpage(t('stake_credits'), contentHtml);
  setTimeout(() => {
    document.getElementById('save-stake').addEventListener('click', async () => {
      const credits = parseFloat(document.getElementById('stake-credits').value);
      const days = parseInt(document.getElementById('stake-days').value);
      if (!credits || credits <= 0 || !days || days <= 0) { alert(t('please_input_all')); return; }
      try {
        const data = await api.stakeCredits(credits, days);
        alert(`${t('save_success')} ${data.expected_reward.toFixed(2)} ${t('credits')}`);
        window.closeSubpage();
        openWallet();
      } catch (e) {
        alert(t('save_failed') + ': ' + e.message);
      }
    });
  }, 100);
}