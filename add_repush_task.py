p = 'core/bootstrap.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 1. 加函数
new_func = '''

async def periodic_task_repush():
    """每小时重播超过 12 小时未完成的任务"""
    from .services import group_task_service
    while True:
        try:
            await asyncio.sleep(3600)
            repushed = await asyncio.to_thread(group_task_service.repush_pending_tasks, 12)
            if repushed:
                print(f'[task-repush] 重播 {len(repushed)} 个任务: {repushed}')
        except Exception as e:
            print(f'[task-repush] error: {e}')
            await asyncio.sleep(3600)
'''

anchor = 'async def periodic_group_red_packet():'
if 'async def periodic_task_repush' in c:
    print('1. function already exists')
elif anchor not in c:
    print('1. anchor not found')
else:
    idx = c.find(anchor)
    c = c[:idx] + new_func.lstrip() + '\n\n' + c[idx:]
    print('1. function inserted')

# 2. 挂载定时任务
old_call = "    rp_expire_task = asyncio.create_task(periodic_red_packet_expire())"
new_call = "    rp_expire_task = asyncio.create_task(periodic_red_packet_expire())\n    task_repush = asyncio.create_task(periodic_task_repush())"

if old_call not in c:
    print('2. call anchor not found')
elif 'task_repush = asyncio.create_task' in c:
    print('2. already registered')
else:
    c = c.replace(old_call, new_call, 1)
    print('2. task registered')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('done')