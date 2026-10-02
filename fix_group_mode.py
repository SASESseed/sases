p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    lines = f.readlines()

out = []
i = 0
while i < len(lines):
    line = lines[i]
    # 找 if (mode === 'swarm') {
    if "if (mode === 'swarm')" in line:
        # 跳过这个 if 块（到下一个单独的 }）
        j = i + 1
        while j < len(lines) and lines[j].strip() != '}':
            j += 1
        # 跳过整个 if 块（含闭合 }）
        i = j + 1
        # 插入 Toast 提示（缩进 4 空格）
        out.append("    if (typeof window.showGroupToast === 'function') {\n")
        out.append("      window.showGroupToast(mode === 'swarm' ? '已切换到蜂群模式' : '已切换到普通模式');\n")
        out.append("    }\n")
        continue
    out.append(line)
    i += 1

with open(p, 'w', encoding='utf-8') as f:
    f.writelines(out)
print('done')