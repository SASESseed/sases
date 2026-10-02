p = 'static/modules/chat_menu.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 找群红包 items.push
old = """items.push({
      icon: '🧧',
      label: '群红包',
      action: () => {
        if (typeof window.openGroupRedPacketDialog === 'function') window.openGroupRedPacketDialog(window.currentGroupId);
      }
    });"""

new = """items.push({
      icon: '🧧',
      label: '群红包',
      badge_id: 'rp-badge',
      action: () => {
        if (typeof window.openGroupRedPacketDialog === 'function') window.openGroupRedPacketDialog(window.currentGroupId);
      }
    });"""

c = c.replace(old, new)

# 在渲染 item HTML 时支持 badge
old_item = """      html += `
        <div class="chat-plus-item">
          <div class="chat-plus-icon">${item.icon}</div>
          <div class="chat-plus-label">${item.label}</div>
        </div>
      `;"""

new_item = """      html += `
        <div class="chat-plus-item"${item.badge_id ? ' data-badge-id="' + item.badge_id + '"' : ''}>
          <div class="chat-plus-icon">${item.icon}${item.badge_id ? '<span class="chat-plus-badge" data-badge="' + item.badge_id + '" style="display:none;"></span>' : ''}</div>
          <div class="chat-plus-label">${item.label}</div>
        </div>
      `;"""

c = c.replace(old_item, new_item)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('done')