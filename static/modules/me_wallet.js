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
      <div class="me-menu-item" id="wallet-seed-entry"><span class="menu-icon">🌱</span><span class="menu-label">种子积分明细</span><span class="menu-arrow">></span></div>
      <div class="me-menu-item" id="wallet-compute-detail-entry"><span class="menu-icon">⚡</span><span class="menu-label">算力积分明细</span><span class="menu-arrow">></span></div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="credit-risk-entry"><span class="menu-icon">⚠️</span><span class="menu-label">积分风险与使用说明</span><span class="menu-arrow">></span></div>
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
    const _seedCard = document.querySelectorAll('.wallet-card')[0];
    if (_seedCard) _seedCard.style.cursor = 'pointer';
    if (_seedCard) _seedCard.onclick = () => openCreditDetail('seed');
    const _computeCard = document.getElementById('wallet-compute-entry');
    if (_computeCard) _computeCard.onclick = () => openCreditDetail('compute');
    document.getElementById('credit-risk-entry').onclick = openCreditRiskPage;
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
  window.openSubpage(t('exchange'), contentHtml, {
    rightBtn: { text: '记录', onclick: () => showActionHistory('exchange') }
  });
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
  window.openSubpage(t('stake'), contentHtml, {
    rightBtn: { text: '记录', onclick: () => showActionHistory('stake') }
  });
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


async function showActionHistory(kind) {
  const title = kind === 'exchange' ? '兑换记录' : '质押记录';
  const kw = kind === 'exchange' ? '兑换' : '质押';
  let history = [];
  try {
    const data = await api.getCreditHistory(50);
    history = (data.history || []).filter(h => (h.action || '').includes(kw));
  } catch (e) {}
  const html = history.length === 0 ? '<div class="subpage-placeholder">暂无' + title + '</div>' : '<div class="me-menu">' + history.map(h => {
    const date = h.created_at ? new Date(h.created_at).toLocaleString('zh-CN') : '';
    const sign = h.points > 0 ? '+' : '';
    const color = h.points > 0 ? '#34c759' : '#ff3b30';
    return '<div class="me-menu-item"><div class="menu-text"><div class="menu-title">' + (h.action || '') + '</div><div class="menu-desc">' + date + '</div></div><span class="menu-value" style="color:' + color + ';">' + sign + h.points + '</span></div>';
  }).join('') + '</div>';
  window.openSubpage(title, html, { showMore: false });
}


async function openCreditDetail(kind) {
  const title = kind === 'seed' ? '种子积分明细' : '算力积分明细';
  let history = [];
  try {
    const data = await api.getCreditHistory(50);
    history = data.history || [];
  } catch (e) {}
  const isStake = h => (h.action || '').includes('质押') || (h.action || '').includes('stake');
  const income = history.filter(h => (h.points || 0) > 0 && !isStake(h));
  const expense = history.filter(h => (h.points || 0) < 0 && !isStake(h));
  const stake = history.filter(isStake);
  const render = (arr, empty) => arr.length === 0 ? '<div class="subpage-placeholder">' + empty + '</div>' : '<div class="me-menu">' + arr.map(h => {
    const date = h.created_at ? new Date(h.created_at).toLocaleString('zh-CN') : '';
    const sign = h.points > 0 ? '+' : '';
    const color = h.points > 0 ? '#34c759' : '#ff3b30';
    return '<div class="me-menu-item"><div class="menu-text"><div class="menu-title">' + (h.action || '积分变动') + '</div><div class="menu-desc">' + date + '</div></div><span class="menu-value" style="color:' + color + ';">' + sign + h.points + '</span></div>';
  }).join('') + '</div>';
  const html = '<div class="me-menu">' +
    '<div class="me-menu-item tab-btn" id="tab-income" style="flex:1;justify-content:center;">获取 (' + income.length + ')</div>' +
    '<div class="me-menu-item tab-btn" id="tab-expense" style="flex:1;justify-content:center;">消耗 (' + expense.length + ')</div>' +
    '<div class="me-menu-item tab-btn" id="tab-stake" style="flex:1;justify-content:center;">质押 (' + stake.length + ')</div>' +
    '</div>' +
    '<div id="credit-list">' + render(income, '暂无获取记录') + '</div>';
  window.openSubpage(title, html, { showMore: false, returnAction: () => openWallet() });
  const list = document.getElementById('credit-list');
  const setActive = (id) => {
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(id).classList.add('active');
  };
  document.getElementById('tab-income').onclick = () => { list.innerHTML = render(income, '暂无获取记录'); setActive('tab-income'); };
  document.getElementById('tab-expense').onclick = () => { list.innerHTML = render(expense, '暂无消耗记录'); setActive('tab-expense'); };
  document.getElementById('tab-stake').onclick = () => { list.innerHTML = render(stake, '暂无质押记录'); setActive('tab-stake'); };
  setActive('tab-income');
}


function openCreditRiskPage() {
  const html = '<div style="padding:12px 16px;font-size:14px;line-height:1.8;color:#333;">' +
    '<h3 style="font-size:15px;margin:16px 0 8px;color:#007aff;">一、积分性质</h3>' +
    '<p>1. 种子积分、算力积分均为 SASES 平台内的虚拟权益，不构成任何形式的法定货币、数字货币或金融资产。</p>' +
    '<p>2. 积分不可兑换人民币、外币、贵金属或任何实物，亦不可通过任何第三方渠道变现。</p>' +
    '<p>3. 积分不具备货币的储值、支付、流通功能，不得用于购买平台外商品或服务。</p>' +
    '<h3 style="font-size:15px;margin:16px 0 8px;color:#007aff;">二、获取与消耗</h3>' +
    '<p>4. 种子积分通过授粉回流、挑坏果子反馈、任务贡献等行为获取。</p>' +
    '<p>5. 算力积分通过种子积分兑换获取，兑换后不可逆。</p>' +
    '<p>6. 积分消耗途径包括：优先调度、定制种子、官方模型调用等。</p>' +
    '<p>7. 所有积分的产出与消耗记录均在对应明细页可查。</p>' +
    '<h3 style="font-size:15px;margin:16px 0 8px;color:#007aff;">三、限制与风险</h3>' +
    '<p>8. 积分不设保底价值，平台有权调整获取/消耗规则。</p>' +
    '<p>9. 积分不可转让、不可继承、不可跨账户合并。</p>' +
    '<p>10. 以下行为将导致积分冻结或清零：作弊刷量、漏洞套利、洗钱赌博、扰乱生态。</p>' +
    '<p>11. 平台如遇不可抗力，积分可能失效且不承担赔偿责任。</p>' +
    '<p>12. 积分账户连续 12 个月无活动，平台有权归档或清零。</p>' +
    '<h3 style="font-size:15px;margin:16px 0 8px;color:#007aff;">四、免责</h3>' +
    '<p>13. 用户应自行判断积分使用风险，操作失误导致的损失平台不承担责任。</p>' +
    '<p>14. 平台不对第三方声称的积分变现行为背书。</p>' +
    '<p>15. 本提示最终解释权归 SASES 平台所有。</p>' +
    '<h3 style="font-size:15px;margin:16px 0 8px;color:#007aff;">五、合规声明</h3>' +
    '<p>16. 积分系统严格遵守相关法律法规，不涉及虚拟货币发行、交易或融资。</p>' +
    '<p>17. 积分不可用于任何博彩、传销、非法集资活动。</p>' +
    '<p>18. 如监管部门要求调整，平台将依法配合执行。</p>' +
    '</div>';
  window.openSubpage('积分风险与使用说明', html, { showMore: false, returnAction: () => openWallet() });
}