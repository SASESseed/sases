p = 'core/services/group_service.py'
with open(p, encoding='utf-8') as f:
    lines = f.readlines()

out = []
i = 0
while i < len(lines):
    line = lines[i]
    if "if mode == 'swarm':" in line and i + 1 < len(lines):
        # 检查下一行是否是拦截
        if '暂未开放' in lines[i + 1]:
            # 跳过这两行
            print(f'skipped lines {i+1}-{i+2}')
            i += 2
            continue
    out.append(line)
    i += 1

with open(p, 'w', encoding='utf-8') as f:
    f.writelines(out)
print('done')