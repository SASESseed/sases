p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 在 leaveGroupEntry 事件绑定后插入新的事件绑定 + 权限判断
anchor = "  const leaveGroupEntry = document.getElementById('leave-group-entry');"
idx = c.find(anchor)
if idx < 0:
    print('anchor not found')
else:
    # 找该 if 块的结束
    end_marker = "if (leaveGroupEntry) leaveGroupEntry.addEventListener('click', leaveGroup);"
    end_idx = c.find(end_marker, idx)
    if end_idx < 0:
        print('end marker not found')
    else:
        end_idx += len(end_marker)
        new_code = """

  // 权限判断：群主/管理员
  let _isOwnerOrAdmin = false;
  let _isOwner = false;
  try {
    const _grpInfo = await api.getGroupInfo(currentGroupId);
    if (_grpInfo && _grpInfo.owner_id != null) {
      _isOwner = String(_grpInfo.owner_id) === String(currentUserId);
      // 管理员判断：role='admin'（若后端支持）
      // 当前先只判断群主，管理员后续扩展
      _isOwnerOrAdmin = _isOwner;
    }
  } catch (e) {}

  // 群知识库（所有成员可见）
  const _gkEntry = document.getElementById('group-knowledge-entry');
  if (_gkEntry) {
    _gkEntry.addEventListener('click', () => {
      if (typeof window.openGroupKnowledge === 'function') {
        window.openGroupKnowledge(currentGroupId);
      } else {
        alert('群知识库开发中');
      }
    });
  }

  // 蜂群模式管理（仅群主可见）
  const _scEntry = document.getElementById('swarm-config-entry');
  if (_scEntry) {
    if (_isOwner) {
      _scEntry.style.display = '';
      _scEntry.addEventListener('click', () => {
        if (typeof window.openSwarmConfig === 'function') {
          window.openSwarmConfig(currentGroupId);
        } else {
          alert('蜂群模式管理开发中');
        }
      });
    } else {
      _scEntry.style.display = 'none';
    }
  }

  // 群管理（群主/管理员可见）
  const _gmEntry = document.getElementById('group-manage-entry');
  if (_gmEntry) {
    if (_isOwnerOrAdmin) {
      _gmEntry.style.display = '';
      _gmEntry.addEventListener('click', () => {
        if (typeof window.openGroupManage === 'function') {
          window.openGroupManage(currentGroupId);
        } else {
          alert('群管理开发中');
        }
      });
    } else {
      _gmEntry.style.display = 'none';
    }
  }"""
        c = c[:end_idx] + new_code + c[end_idx:]
        with open(p, 'w', encoding='utf-8') as f:
            f.write(c)
        print('bound OK')