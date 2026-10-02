import re

p = 'static/modules/me_wallet.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 1. 删除 UI 上的 menu-stake 行
c = re.sub(r'\n\s*<div class="me-menu-item" id="menu-stake">[^\n]*</div>', '', c)

# 2. 删除事件绑定
c = c.replace("    document.getElementById('menu-stake').onclick = openStakePage;\n", "")

# 3. 删除 openStakePage 函数
start = c.find('function openStakePage() {')
if start >= 0:
    # 找函数结束：下一个 "\n}\n"
    end = c.find('\n}\n', start)
    if end >= 0:
        end += 3
        c = c[:start] + c[end:]

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)

print('done')