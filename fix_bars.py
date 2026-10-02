p = 'static/index.html'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 旧块：从 group-task-bar 开头到 group-red-packet-bar 闭合
old_block = '''          <div id="group-task-bar" class="group-task-bar" style="display:none;">

          </div>
          <div id="group-red-packet-bar" class="group-task-bar" style="display:none;background:linear-gradient(135deg,#f59e0b,#ef4444);">
            <span class="group-task-bar-text" id="group-red-packet-bar-text">待抢红包</span>
            <span class="group-task-bar-arrow">▾</span>
            <span class="group-task-bar-text" id="group-task-bar-text">进行中任务</span>
            <span class="group-task-bar-arrow">▾</span>
          </div>'''

# 新块：正确结构
new_block = '''          <div id="group-task-bar" class="group-task-bar" style="display:none;">
            <span class="group-task-bar-text" id="group-task-bar-text">进行中任务</span>
            <span class="group-task-bar-arrow">▾</span>
          </div>
          <div id="group-red-packet-bar" class="group-task-bar" style="display:none;background:linear-gradient(135deg,#f59e0b,#ef4444);">
            <span class="group-task-bar-text" id="group-red-packet-bar-text">待抢红包</span>
            <span class="group-task-bar-arrow">▾</span>
          </div>'''

if old_block in c:
    c = c.replace(old_block, new_block)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('replaced OK')
else:
    print('old block not found')