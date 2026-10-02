window.openAnnouncementEditor = async function() {
  const groupId = currentGroupId;
  if (!groupId) return;

  // 权限判断
  let isOwnerOrAdmin = false;
  try {
    const resp = await fetch('/group/' + groupId + '/admins', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    for (const a of (data.admins || [])) {
      if (String(a.user_id) === String(currentUserId)) {
        if (a.role === 'owner' || a.role === 'admin') isOwnerOrAdmin = true;
        break;
      }
    }
  } catch (e) {}

  // 读公告
  let content = '';
  try {
    const resp = await fetch('/group/' + groupId + '/announcement', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    content = data.announcement || '';
  } catch (e) {}

  if (isOwnerOrAdmin) {
    const html = `
      <div class="me-menu">
        <div class="me-menu-item" style="display:block;padding:12px;">
          <textarea id="announcement-input" rows="10" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;resize:vertical;" placeholder="点击输入群公告，最多 2000 字">${content}</textarea>
        </div>
      </div>
      <button class="save-btn" id="announcement-save">保存</button>
    `;
    window.openSubpage('群公告', html, {
      returnAction: () => openGroupSettings()
    });
    setTimeout(() => {
      const btn = document.getElementById('announcement-save');
      if (!btn) return;
      btn.onclick = async () => {
        const newContent = (document.getElementById('announcement-input') || {}).value || '';
        try {
          const resp = await fetch('/group/' + groupId + '/announcement', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: newContent })
          });
          const data = await resp.json();
          if (data.error || data.detail) { alert('保存失败：' + (data.error || data.detail)); return; }
          alert('已保存');
          window.closeSubpage();
        } catch (e) { alert('网络错误：' + e.message); }
      };
    }, 300);
  } else {
    const html = content
      ? '<div class="me-menu"><div class="me-menu-item" style="display:block;padding:14px;font-size:14px;color:#333;line-height:1.7;white-space:pre-wrap;">' + content + '</div></div>'
      : '<div class="subpage-placeholder">暂无群公告</div>';
    window.openSubpage('群公告', html, {
      returnAction: () => openGroupSettings()
    });
  }
};