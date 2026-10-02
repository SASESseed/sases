p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

start = c.find('function openGroupModeMenu() {')
if start < 0:
    start = c.find('async function openGroupModeMenu() {')
if start < 0:
    print('start not found')
else:
    end = c.find('function closeGroupModeMenu() {', start)
    if end < 0:
        print('end not found')
    else:
        new_func = '''async function openGroupModeMenu() {
  const menu = document.getElementById('mode-menu');
  const content = document.getElementById('mode-menu-content');
  if (!menu || !content) return;

  let swarmEnabled = false;
  try {
    const r = await fetch('/group/' + currentGroupId + '/swarm/status', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const d = await r.json();
    swarmEnabled = !!d.swarm_enabled;
  } catch (e) {}

  const normalHtml = '<div class="plus-menu-item mode-item ' + (currentGroupMode === 'normal' ? 'active-mode' : '') + '" data-mode="normal"><span class="plus-menu-label">普通聊天</span></div>';
  const swarmHtml = swarmEnabled ? '<div class="plus-menu-item mode-item ' + (currentGroupMode === 'swarm' ? 'active-mode' : '') + '" data-mode="swarm"><span class="plus-menu-label">蜂群模式</span></div>' : '';
  content.innerHTML = normalHtml + swarmHtml;

  const modeBtn = document.getElementById('chat-mode-btn');
  if (modeBtn) {
    const rect = modeBtn.getBoundingClientRect();
    content.style.left = rect.left + 'px';
    content.style.top = (rect.bottom + 5) + 'px';
    content.style.position = 'fixed';
  }

  menu.style.display = 'block';
  document.getElementById('mode-menu-overlay').onclick = closeGroupModeMenu;

  content.querySelectorAll('.mode-item').forEach(el => {
    el.addEventListener('click', async () => {
      const mode = el.dataset.mode;
      await applyGroupMode(mode);
      closeGroupModeMenu();
    });
  });
}

'''
        c = c[:start] + new_func + c[end:]
        with open(p, 'w', encoding='utf-8') as f:
            f.write(c)
        print('replaced OK')