p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 锚点：群排行榜 entry 之后，其 me-menu 块的结束 </div> 之后插入新块
anchor = '<div class="me-menu-item" id="group-leaderboard-entry">'
idx = c.find(anchor)
if idx < 0:
    print('anchor not found')
else:
    # 找该行的结束（第一个 \n 或 \r\n）
    line_end = c.find('\n', idx)
    if line_end < 0:
        print('line end not found')
    else:
        # 再找下一个 </div>（me-menu 块的结束）
        menu_end = c.find('</div>', line_end)
        menu_end += len('</div>')
        new_block = """

      <div class="me-menu">
        <div class="me-menu-item" id="group-knowledge-entry"><span class="menu-icon">📚</span><span class="menu-label">群知识库</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="swarm-config-entry" style="display:none;"><span class="menu-icon">⚙️</span><span class="menu-label">蜂群模式管理</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="group-manage-entry" style="display:none;"><span class="menu-icon">👥</span><span class="menu-label">群管理</span><span class="menu-arrow">›</span></div>
      </div>"""
        c = c[:menu_end] + new_block + c[menu_end:]
        with open(p, 'w', encoding='utf-8') as f:
            f.write(c)
        print('inserted OK')