window.openGroupRedPacketDialog = function(groupId) {
  const html = `
    <div style="padding:16px;">
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">红包类型</div>
        <select id="grp-rp-type" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff;">
          <option value="lucky">拼手气红包（金额随机）</option>
          <option value="normal">普通红包（金额均分）</option>
        </select>
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">红包总金额（积分）</div>
        <input id="grp-rp-total" type="number" value="10" min="1" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;">
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">红包个数</div>
        <input id="grp-rp-count" type="number" value="5" min="1" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;">
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">留言（可选）</div>
        <input id="grp-rp-msg" type="text" placeholder="恭喜发财，大吉大利" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;">
      </div>
      <div style="background:#fff7e6;border:1px solid #ffd591;border-radius:6px;padding:10px;margin-bottom:20px;font-size:12px;color:#874d00;line-height:1.6;">
        ⚠️ 红包 24 小时内有效，未领完的金额将退回你的积分账户。
      </div>
      <button id="grp-rp-submit" style="width:100%;padding:12px;background:#ef4444;color:#fff;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;">塞钱进红包</button>
    </div>
  `;
  window.openSubpage('发群红包', html);
  setTimeout(function() {
    const btn = document.getElementById('grp-rp-submit');
    if (!btn) return;
    btn.onclick = function() {
      const type = document.getElementById('grp-rp-type').value;
      const total = parseFloat(document.getElementById('grp-rp-total').value);
      const count = parseInt(document.getElementById('grp-rp-count').value);
      const msg = document.getElementById('grp-rp-msg').value || '';
      if (!total || total < 1) { alert('总金额最少 1'); return; }
      if (!count || count < 1) { alert('个数最少 1'); return; }
      fetch('/group/' + groupId + '/red-packets/create', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
        body: JSON.stringify({ total_amount: total, total_count: count, message: msg, source_type: 'user', packet_type: type })
      }).then(r => r.json()).then(data => {
        if (data.error || data.detail) { alert('发布失败：' + (data.error || data.detail)); return; }
        alert('红包已发送');
        if (typeof window.closeSubpage === 'function') window.closeSubpage();
        if (typeof loadGroupMessages === 'function') loadGroupMessages();
      }).catch(e => alert('网络错误：' + e.message));
    };
  }, 300);
};