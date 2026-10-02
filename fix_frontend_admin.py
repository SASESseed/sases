p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 替换权限判断块
old_block = """  let _isOwnerOrAdmin = false;
  let _isOwner = false;
  try {
    const _grpInfo = await api.getGroupInfo(currentGroupId);
    if (_grpInfo && _grpInfo.owner_id != null) {
      _isOwner = String(_grpInfo.owner_id) === String(currentUserId);
      // 管理员判断：role='admin'（若后端支持）
      // 当前先只判断群主，管理员后续扩展
      _isOwnerOrAdmin = _isOwner;
    }
  } catch (e) {}"""

new_block = """  let _isOwnerOrAdmin = false;
  let _isOwner = false;
  try {
    const _resp = await fetch('/group/' + currentGroupId + '/admins', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const _data = await _resp.json();
    const _admins = _data.admins || [];
    for (const a of _admins) {
      if (String(a.user_id) === String(currentUserId)) {
        if (a.role === 'owner') {
          _isOwner = true;
          _isOwnerOrAdmin = true;
        } else if (a.role === 'admin') {
          _isOwnerOrAdmin = true;
        }
        break;
      }
    }
  } catch (e) {}"""

if old_block not in c:
    print('old block not found')
else:
    c = c.replace(old_block, new_block)
    # 蜂群模式管理：_isOwner 改成 _isOwnerOrAdmin
    old_sc = """    if (_isOwner) {
      _scEntry.style.display = '';"""
    new_sc = """    if (_isOwnerOrAdmin) {
      _scEntry.style.display = '';"""
    c = c.replace(old_sc, new_sc)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('done')