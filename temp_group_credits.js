async function openGroupCreditsDetail() {
  let pool = { available: 0, staked: 0, total: 0, red_packet_hour: 20, red_packet_audience: 'all' };
  try {
    const resp = await fetch('/group/' + currentGroupId + '/pool', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    pool = await resp.json();
  } catch (e) {}
  const contentHtml = `
    <div class="wallet-card" style="background: linear-gradient(135deg, #007aff, #00c6ff);">
      <div class="wallet-label">可用积分</div>
      <div class="wallet-balance">${pool.available || 0}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:4px;">用于发任务、发红包</div>
    </div>
    <div class="wallet-card" style="background: linear-gradient(135deg, #667eea, #764ba2);">
      <div class="wallet-label">质押总额</div>
      <div class="wallet-balance">${pool.staked || 0}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:4px;">锁定期 30 天，到期可提取</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="gc-stake-entry">
        <span class="menu-icon">💰</span>
        <span class="menu-label">质押积分</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item">
        <span class="menu-icon">📊</span>
        <span class="menu-label">总积分</span>
        <span class="menu-value">${pool.total || 0}</span>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="gc-redpacket-config">
        <span class="menu-icon">🧧</span>
        <span class="menu-label">红包配置</span>
        <span class="menu-value">${pool.red_packet_hour || 20}:00</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="gc-send-redpacket">
        <span class="menu-icon">🎁</span>
        <span class="menu-label">立即发红包（群主）</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
    <div class="section-title">积分说明</div>
    <div style="padding:12px;font-size:13px;color:#666;line-height:1.8;">
      • 任务抽成 5% 进入群池<br>
      • 每日空投按活跃度竞争（10000 分/天）<br>
      • 可用余额满 1000 可发群红包
    </div>
  `;
  window.openSubpage('群积分', contentHtml, { showMore: false });
  setTimeout(() => {
    const stake = document.getElementById('gc-stake-entry');
    if (stake) stake.onclick = openGroupStakeDialog;
    const config = document.getElementById('gc-redpacket-config');
    if (config) config.onclick = openRedPacketConfig;
    const send = document.getElementById('gc-send-redpacket');
    if (send) send.onclick = sendRedPacketNow;
  }, 100);
}

function openGroupStakeDialog() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">质押金额（最少 10）</span>
        <input type="number" id="gc-stake-amount" class="inline-input" value="10" min="10">
      </div>
    </div>
    <div style="padding:12px;font-size:12px;color:#666;line-height:1.6;">
      质押积分锁定 30 天，到期后可提取。质押后该群获得空投资格（需总积分≥100）。
    </div>
    <button class="save-btn" id="gc-stake-submit">质押</button>
  `;
  window.openSubpage('质押积分', contentHtml);
  setTimeout(() => {
    const btn = document.getElementById('gc-stake-submit');
    if (!btn) return;
    btn.onclick = async () => {
      const amount = parseFloat(document.getElementById('gc-stake-amount').value);
      if (!amount || amount < 10) { alert('最少质押 10'); return; }
      try {
        const resp = await fetch('/group/' + currentGroupId + '/stake', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount: amount })
        });
        const data = await resp.json();
        if (data.error || data.detail) { alert('质押失败：' + (data.error || data.detail)); return; }
        alert('质押成功');
        window.closeSubpage();
        openGroupCreditsDetail();
      } catch (e) { alert('网络错误：' + e.message); }
    };
  }, 100);
}

function openRedPacketConfig() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">发放时间（0-23 点）</span>
        <input type="number" id="gc-rp-hour" class="inline-input" value="20" min="0" max="23">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">谁可以抢</span>
        <select id="gc-rp-audience" class="inline-input">
          <option value="all">所有群成员</option>
          <option value="stakers">仅质押成员</option>
        </select>
      </div>
    </div>
    <button class="save-btn" id="gc-rp-save">保存配置</button>
  `;
  window.openSubpage('红包配置', contentHtml);
  setTimeout(() => {
    const btn = document.getElementById('gc-rp-save');
    if (!btn) return;
    btn.onclick = async () => {
      const hour = parseInt(document.getElementById('gc-rp-hour').value);
      const audience = document.getElementById('gc-rp-audience').value;
      if (isNaN(hour) || hour < 0 || hour > 23) { alert('小时必须 0-23'); return; }
      try {
        const resp = await fetch('/group/' + currentGroupId + '/red-packet/config', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
          body: JSON.stringify({ hour: hour, audience: audience })
        });
        const data = await resp.json();
        if (data.error || data.detail) { alert('保存失败：' + (data.error || data.detail)); return; }
        alert('已保存');
        window.closeSubpage();
        openGroupCreditsDetail();
      } catch (e) { alert('网络错误：' + e.message); }
    };
  }, 100);
}

function sendRedPacketNow() {
  if (!confirm('确定立即发放群红包？群池可用余额将均分给符合受众的成员。')) return;
  fetch('/group/' + currentGroupId + '/red-packet/send', {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
  }).then(r => r.json()).then(data => {
    if (data.error || data.detail) { alert('发放失败：' + (data.error || data.detail)); return; }
    alert('已发放 ' + data.total + ' 积分给 ' + data.recipients + ' 人');
    window.closeSubpage();
    openGroupCreditsDetail();
  }).catch(e => alert('网络错误：' + e.message));
}