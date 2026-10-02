window.openGroupManage = async function(groupId) {
  let admins = [];
  let members = [];
  let groupInfo = {};

  try {
    const r1 = await fetch('/group/' + groupId + '/admins', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const d1 = await r1.json();
    admins = d1.admins || [];
  } catch (e) {}

  try {
    const r2 = await fetch('/group/' + groupId + '/members', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const d2 = await r2.json();
    members = d2.members || [];
  } catch (e) {}

  try {
    const r3 = await api.getGroupInfo(groupId);
    groupInfo = r3 || {};
  } catch (e) {}

  const isOwner = groupInfo.owner_id != null && String(groupInfo.owner_id) === String(currentUserId);

  // 渲染管理员列表
  let adminsHtml = '';
  admins.forEach(a => {
    const roleLabel = a.role === 'owner' ? '群主' : '管理员';
    adminsHtml += '<div class="me-menu-item">';
    adminsHtml += '<span class="menu-label">' + (a.username || '用户') + '</span>';
    adminsHtml += '<span class="menu-value">' + roleLabel + '</span>';
    if (a.role === 'admin' && isOwner) {
      adminsHtml += '<span class="remove-admin-btn" data-uid="' + a.user_id + '" style="color:#ff3b30;font-size:13px;margin-left:8px;cursor:pointer;">移除</span>';
    }
    adminsHtml += '</div>';
  });

  const html = `
    <div class="me-menu">
      <div class="me-menu-item" id="gm-announcement" style="cursor:pointer;">
        <span class="menu-label">群公告</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="gm-invite-confirm" style="cursor:pointer;">
        <span class="menu-label">群聊邀请确认</span>
        <div class="switch"><div class="slider"></div></div>
      </div>
    </div>
    <div class="section-title">群管理员</div>
    <div class="me-menu" id="gm-admins-list">
      ${adminsHtml}
    </div>
    ${isOwner ? '<div class="me-menu"><div class="me-menu-item" id="gm-add-admin" style="cursor:pointer;"><span class="menu-label" style="color:#007aff;">+ 添加管理员</span></div></div>' : ''}
    <div class="me-menu">
      <div class="me-menu-item" id="gm-qrcode" style="cursor:pointer;">
        <span class="menu-label">群二维码</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="gm-transfer" style="cursor:pointer;">
        <span class="menu-label">群主管理权转让</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="gm-remove-log" style="cursor:pointer;">
        <span class="menu-label">移出群聊记录</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
  `;

  window.openSubpage('群管理', html, {
    showMore: false,
    returnAction: () => openGroupSettings()
  });

  setTimeout(() => {
    const ann = document.getElementById('gm-announcement');
    if (ann) ann.onclick = () => alert('群公告开发中');

    const inv = document.getElementById('gm-invite-confirm');
    if (inv) inv.onclick = () => alert('邀请确认开关开发中');

    const addAdmin = document.getElementById('gm-add-admin');
    if (addAdmin) {
      addAdmin.onclick = () => openAddAdminDialog(groupId, members, admins);
    }

    document.querySelectorAll('.remove-admin-btn').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const uid = btn.dataset.uid;
        if (!confirm('确定移除该管理员？')) return;
        try {
          const resp = await fetch('/group/' + groupId + '/members/role', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({ username_or_id: String(uid), role: 'member' })
          });
          const data = await resp.json();
          if (data.error || data.detail) { alert('移除失败：' + (data.error || data.detail)); return; }
          alert('已移除');
          window.openGroupManage(groupId);
        } catch (err) { alert('网络错误：' + err.message); }
      };
    });

    const qr = document.getElementById('gm-qrcode');
    if (qr) qr.onclick = () => alert('群二维码开发中');

    const tr = document.getElementById('gm-transfer');
    if (tr) tr.onclick = () => alert('群主转让开发中');

    const rl = document.getElementById('gm-remove-log');
    if (rl) rl.onclick = () => alert('移出记录开发中');
  }, 300);
};

window.openAddAdminDialog = function(groupId, members, currentAdmins) {
  const adminIds = new Set(currentAdmins.map(a => String(a.user_id)));
  const candidates = members.filter(m => m.user_id && !adminIds.has(String(m.user_id)) && m.role !== 'owner');

  let listHtml = '';
  if (candidates.length === 0) {
    listHtml = '<div class="subpage-placeholder">没有可添加的成员</div>';
  } else {
    candidates.forEach(m => {
      listHtml += '<div class="me-menu-item add-admin-item" data-uid="' + m.user_id + '" style="cursor:pointer;">';
      listHtml += '<span class="menu-label">' + (m.display_name || m.username || ('用户 ' + m.user_id)) + '</span>';
      listHtml += '<span class="menu-arrow">›</span>';
      listHtml += '</div>';
    });
  }

  const html = `
    <div class="me-menu">
      ${listHtml}
    </div>
  `;

  window.openSubpage('添加管理员', html, {
    showMore: false,
    returnAction: () => window.openGroupManage(groupId)
  });

  setTimeout(() => {
    document.querySelectorAll('.add-admin-item').forEach(el => {
      el.onclick = async () => {
        const uid = el.dataset.uid;
        try {
          const resp = await fetch('/group/' + groupId + '/members/role', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({ username_or_id: uid, role: 'admin' })
          });
          const data = await resp.json();
          if (data.error || data.detail) { alert('添加失败：' + (data.error || data.detail)); return; }
          alert('已添加为管理员');
          window.openGroupManage(groupId);
        } catch (err) { alert('网络错误：' + err.message); }
      };
    });
  }, 300);
};