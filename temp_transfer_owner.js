window.openTransferOwnerDialog = async function(groupId) {
  // 拉群成员
  let members = [];
  try {
    const resp = await fetch('/group/' + groupId + '/members', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    members = (data.members || []).filter(m => m.user_id && String(m.user_id) !== String(currentUserId));
  } catch (e) {}

  let listHtml = '';
  if (members.length === 0) {
    listHtml = '<div class="subpage-placeholder">没有可转让的成员</div>';
  } else {
    members.forEach(m => {
      listHtml += '<div class="me-menu-item transfer-owner-item" data-uid="' + m.user_id + '" style="cursor:pointer;">';
      listHtml += '<span class="menu-label">' + (m.display_name || m.username || ('用户 ' + m.user_id)) + '</span>';
      listHtml += '<span class="menu-arrow">›</span>';
      listHtml += '</div>';
    });
  }

  const html = `
    <div style="padding:12px;font-size:12px;color:#ff3b30;line-height:1.6;">
      ⚠️ 转让后你将成为管理员，新群主拥有完整权限。
    </div>
    <div class="me-menu">
      ${listHtml}
    </div>
  `;

  window.openSubpage('转让群主', html, {
    showMore: false,
    returnAction: () => window.openGroupManage(groupId)
  });

  setTimeout(() => {
    document.querySelectorAll('.transfer-owner-item').forEach(el => {
      el.onclick = async () => {
        const uid = el.dataset.uid;
        if (!confirm('确定将群主转让给该成员？转让后你将成为管理员，此操作不可撤销！')) return;
        try {
          const resp = await fetch('/group/' + groupId + '/transfer-owner', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({ username_or_id: String(uid) })
          });
          const data = await resp.json();
          if (data.error || data.detail) { alert('转让失败：' + (data.error || data.detail)); return; }
          alert('已转让');
          window.closeSubpage();
          window.openGroupManage(groupId);
        } catch (e) { alert('网络错误：' + e.message); }
      };
    });
  }, 300);
};