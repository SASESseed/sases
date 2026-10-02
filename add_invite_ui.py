p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

changes = 0

# 1. 替换开关绑定
old1 = """    const inv = document.getElementById('gm-invite-confirm');
    if (inv) inv.onclick = () => alert('邀请确认开关开发中');"""
new1 = """    const inv = document.getElementById('gm-invite-confirm');
    if (inv) inv.onclick = async () => {
      const sw = inv.querySelector('.switch');
      const cur = sw && sw.classList.contains('on');
      try {
        const resp = await fetch('/group/' + groupId + '/invite-confirm', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: !cur })
        });
        const data = await resp.json();
        if (data.error || data.detail) { alert('切换失败：' + (data.error || data.detail)); return; }
        if (sw) {
          if (data.invite_confirm) sw.classList.add('on'); else sw.classList.remove('on');
        }
      } catch (e) { alert('网络错误：' + e.message); }
    };
    // 读取当前开关状态
    fetch('/group/' + groupId + '/invite-confirm', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    }).then(r => r.json()).then(d => {
      const sw = inv && inv.querySelector('.switch');
      if (sw) {
        if (d.enabled) sw.classList.add('on'); else sw.classList.remove('on');
      }
    }).catch(() => {});"""
if old1 in c:
    c = c.replace(old1, new1)
    changes += 1

# 2. HTML 加"待批准邀请"入口（在群管理员 section 之后）
old2 = """    <div class="section-title">群管理员</div>
    <div class="me-menu" id="gm-admins-list">
      ${adminsHtml}
    </div>"""
new2 = """    <div class="section-title">群管理员</div>
    <div class="me-menu" id="gm-admins-list">
      ${adminsHtml}
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="gm-pending-invites" style="cursor:pointer;">
        <span class="menu-label">待批准邀请</span>
        <span class="menu-value" id="gm-pending-count">0</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>"""
if old2 in c:
    c = c.replace(old2, new2)
    changes += 1

# 3. 绑定"待批准邀请"点击 + 拉数量
old3 = """    const addAdmin = document.getElementById('gm-add-admin');"""
new3 = """    const pendingInv = document.getElementById('gm-pending-invites');
    if (pendingInv) {
      pendingInv.onclick = () => {
        if (typeof window.openPendingInvites === 'function') window.openPendingInvites(groupId);
      };
      fetch('/group/' + groupId + '/pending-invites', {
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
      }).then(r => r.json()).then(d => {
        const n = (d.items || []).length;
        const cnt = document.getElementById('gm-pending-count');
        if (cnt) cnt.textContent = n;
      }).catch(() => {});
    }

    const addAdmin = document.getElementById('gm-add-admin');"""
if old3 in c:
    c = c.replace(old3, new3)
    changes += 1

# 4. 追加 openPendingInvites 函数
if 'window.openPendingInvites = ' not in c:
    new_func = '''

window.openPendingInvites = async function(groupId) {
  let items = [];
  try {
    const resp = await fetch('/group/' + groupId + '/pending-invites', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    if (data.error || data.detail) { alert('加载失败：' + (data.error || data.detail)); return; }
    items = data.items || [];
  } catch (e) { alert('网络错误：' + e.message); return; }

  let listHtml = '';
  if (items.length === 0) {
    listHtml = '<div class="subpage-placeholder">暂无待批准邀请</div>';
  } else {
    items.forEach(it => {
      listHtml += '<div class="me-menu-item" style="display:block;padding:12px;">';
      listHtml += '<div style="font-size:14px;color:#333;">' + (it.invitee || '') + '</div>';
      listHtml += '<div style="font-size:12px;color:#999;margin-top:4px;">邀请人：' + (it.inviter_name || '?') + ' · ' + (it.created_at || '') + '</div>';
      listHtml += '<div style="margin-top:10px;display:flex;gap:10px;">';
      listHtml += '<button class="save-btn" style="flex:1;padding:8px;font-size:13px;" data-approve="' + it.id + '">批准</button>';
      listHtml += '<button style="flex:1;padding:8px;font-size:13px;background:#ff3b30;color:#fff;border:none;border-radius:6px;cursor:pointer;" data-reject="' + it.id + '">拒绝</button>';
      listHtml += '</div>';
      listHtml += '</div>';
    });
  }

  const html = '<div class="me-menu">' + listHtml + '</div>';

  window.openSubpage('待批准邀请', html, {
    showMore: false,
    returnAction: () => window.openGroupManage(groupId)
  });

  setTimeout(() => {
    document.querySelectorAll('[data-approve]').forEach(el => {
      el.onclick = async () => {
        const pid = el.dataset.approve;
        try {
          const resp = await fetch('/group/pending-invites/' + pid + '/approve', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({})
          });
          const data = await resp.json();
          if (data.error || data.detail) { alert('批准失败：' + (data.error || data.detail)); return; }
          alert('已批准');
          window.openPendingInvites(groupId);
        } catch (e) { alert('网络错误：' + e.message); }
      };
    });
    document.querySelectorAll('[data-reject]').forEach(el => {
      el.onclick = async () => {
        const pid = el.dataset.reject;
        if (!confirm('确定拒绝该邀请？')) return;
        try {
          const resp = await fetch('/group/pending-invites/' + pid + '/reject', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({})
          });
          const data = await resp.json();
          if (data.error || data.detail) { alert('拒绝失败：' + (data.error || data.detail)); return; }
          alert('已拒绝');
          window.openPendingInvites(groupId);
        } catch (e) { alert('网络错误：' + e.message); }
      };
    });
  }, 300);
};
'''
    with open(p, 'a', encoding='utf-8') as f:
        f.write(new_func)
    changes += 1

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('changes:', changes)