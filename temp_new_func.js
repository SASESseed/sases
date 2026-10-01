window.openPublishTaskDialog = function(groupId) {
  const html = `
    <div style="padding:16px;">
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">任务标题</div>
        <input id="pt-title" type="text" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;" placeholder="请输入标题">
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">任务描述</div>
        <textarea id="pt-desc" rows="3" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;resize:vertical;" placeholder="可选"></textarea>
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">任务类型</div>
        <select id="pt-category" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff;">
          <option value="text">文本</option>
          <option value="image">图片</option>
          <option value="code">代码</option>
          <option value="creative">创意</option>
        </select>
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">质押积分（最少 10）</div>
        <input id="pt-reward" type="number" value="10" min="10" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;">
      </div>
      <div style="background:#fff7e6;border:1px solid #ffd591;border-radius:6px;padding:10px;margin-bottom:20px;font-size:12px;color:#874d00;line-height:1.6;">
        ⚠️ 任务完成后，<b>95%</b> 给被选中的方案提交者，<b>5%</b> 进入群积分池。
      </div>
      <button id="pt-submit" style="width:100%;padding:12px;background:#07c160;color:#fff;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;">发布任务</button>
    </div>
  `;
  window.openSubpage('发布任务', html);
  setTimeout(function() {
    const btn = document.getElementById('pt-submit');
    if (!btn) return;
    btn.onclick = function() {
      const title = (document.getElementById('pt-title') || {}).value || '';
      const desc = (document.getElementById('pt-desc') || {}).value || '';
      const category = (document.getElementById('pt-category') || {}).value || 'text';
      const rewardStr = (document.getElementById('pt-reward') || {}).value || '0';
      if (!title.trim()) { alert('请输入标题'); return; }
      const reward = parseFloat(rewardStr);
      if (isNaN(reward) || reward < 10) { alert('质押积分最少 10'); return; }
      fetch('/group/' + groupId + '/tasks/publish', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim(), description: desc, category: category, reward: reward })
      }).then(r => r.json()).then(data => {
        if (data.error || data.detail) { alert('发布失败：' + (data.error || data.detail)); return; }
        alert('任务已发布');
        if (typeof window.closeSubpage === 'function') window.closeSubpage();
        if (typeof loadGroupMessages === 'function') loadGroupMessages();
      }).catch(e => alert('网络错误：' + e.message));
    };
  }, 100);
};