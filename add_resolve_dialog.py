p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

if 'window.openReportResolveDialog' in c:
    print('already exists')
else:
    new_func = '''

window.openReportResolveDialog = async function(groupId, queueId) {
  let question = '';
  try {
    const resp = await fetch('/group/' + groupId + '/report-queue?status=pending', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    const item = (data.items || []).find(i => i.id === queueId);
    if (item) question = item.question || '';
  } catch (e) {}

  const html = `
    <div class="me-menu">
      <div class="me-menu-item" style="display:block;padding:12px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">问题</div>
        <div style="font-size:14px;color:#333;line-height:1.6;background:#f8f8f8;padding:10px;border-radius:6px;">${question}</div>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" style="display:block;padding:12px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">答案</div>
        <textarea id="report-answer" rows="8" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;resize:vertical;" placeholder="输入答案，将自动加入群知识库"></textarea>
      </div>
    </div>
    <button class="save-btn" id="report-save">保存答案</button>
  `;

  window.openSubpage('补充答案', html, {
    showMore: false,
    returnAction: () => window.openGroupReportQueue(groupId)
  });

  setTimeout(() => {
    const btn = document.getElementById('report-save');
    if (!btn) return;
    btn.onclick = async () => {
      const answer = (document.getElementById('report-answer') || {}).value || '';
      if (!answer.trim()) { alert('答案不能为空'); return; }
      try {
        const resp = await fetch('/group/report-queue/' + queueId + '/resolve', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
          body: JSON.stringify({ answer: answer, category: 'faq' })
        });
        const data = await resp.json();
        if (data.error || data.detail) { alert('保存失败：' + (data.error || data.detail)); return; }
        alert('已保存并加入群知识库');
        window.closeSubpage();
        window.openGroupReportQueue(groupId);
      } catch (e) { alert('网络错误：' + e.message); }
    };
  }, 300);
};
'''

    with open(p, 'a', encoding='utf-8') as f:
        f.write(new_func)
    print('appended OK')