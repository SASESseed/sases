p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

if 'window.openGroupReportQueue = async function' in c:
    print('already defined')
else:
    new_func = '''

window.openGroupReportQueue = async function(groupId) {
  let items = [];
  try {
    const resp = await fetch('/group/' + groupId + '/report-queue?status=pending', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    if (data.error || data.detail) { alert('加载失败：' + (data.error || data.detail)); return; }
    items = data.items || [];
  } catch (e) { alert('网络错误：' + e.message); return; }

  let listHtml = '';
  if (items.length === 0) {
    listHtml = '<div class="subpage-placeholder">暂无待补充问题</div>';
  } else {
    items.forEach(it => {
      const asker = it.anonymous ? '匿名' : (it.username || '群友');
      listHtml += '<div class="me-menu-item report-item" data-qid="' + it.id + '" style="cursor:pointer;">';
      listHtml += '<div style="flex:1;min-width:0;">';
      listHtml += '<div style="font-size:14px;color:#333;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + (it.question || '') + '</div>';
      listHtml += '<div style="font-size:12px;color:#999;margin-top:2px;">来自 ' + asker + '</div>';
      listHtml += '</div>';
      listHtml += '<span class="menu-arrow">›</span>';
      listHtml += '</div>';
    });
  }

  const html = `
    <div class="me-menu">
      ${listHtml}
    </div>
    <div style="padding:12px;font-size:12px;color:#999;line-height:1.6;">
      员工提问时，如果群知识库没有答案，会自动出现在这里。补充答案后，会自动进入群知识库。
    </div>
  `;

  window.openSubpage('群汇报', html, {
    showMore: false,
    returnAction: () => openGroupSettings()
  });

  setTimeout(() => {
    document.querySelectorAll('.report-item').forEach(el => {
      el.onclick = () => window.openReportResolveDialog(groupId, parseInt(el.dataset.qid));
    });
  }, 300);
};
'''

    with open(p, 'a', encoding='utf-8') as f:
        f.write(new_func)
    print('appended OK')