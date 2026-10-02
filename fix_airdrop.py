p = 'core/bootstrap.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 找第一个 periodic_airdrop 定义
first = c.find('async def periodic_airdrop():')
# 找 @asynccontextmanager 位置
end = c.find('@asynccontextmanager', first)
if first < 0 or end < 0:
    print('not found: first=' + str(first) + ' end=' + str(end))
else:
    # 保留一个 periodic_airdrop + 新增 periodic_group_red_packet
    new_block = '''async def periodic_airdrop():
    """每天 0:30 执行空投"""
    from .services import airdrop_service
    while True:
        try:
            from datetime import datetime, timedelta
            dt = datetime.utcnow()
            next_run = dt.replace(hour=0, minute=30, second=0, microsecond=0)
            if next_run <= dt:
                next_run += timedelta(days=1)
            wait_sec = (next_run - dt).total_seconds()
            print(f'[airdrop] next run in {int(wait_sec)}s')
            await asyncio.sleep(wait_sec)
            result = await asyncio.to_thread(airdrop_service.run_daily_airdrop)
            print(f'[airdrop] {result}')
        except Exception as e:
            print(f'[airdrop] error: {e}')
            await asyncio.sleep(3600)


async def periodic_group_red_packet():
    """每分钟检查群红包时间，到点自动发群福利手气红包"""
    from .services import group_red_packet_service
    from .db import db_cursor
    from datetime import datetime
    while True:
        try:
            now = datetime.utcnow()
            today = now.strftime('%Y-%m-%d')
            cur_hour = now.hour
            with db_cursor() as cur:
                cur.execute(
                    "SELECT id, owner_id, credits, red_packet_hour, last_red_packet_date FROM groups WHERE red_packet_hour=? AND (last_red_packet_date IS NULL OR last_red_packet_date != ?) AND COALESCE(credits, 0) >= 100",
                    (cur_hour, today)
                )
                rows = cur.fetchall()
            for g in rows:
                try:
                    amount = round((g['credits'] or 0) * 0.1, 2)
                    if amount < 1:
                        amount = 1.0
                    if amount > (g['credits'] or 0):
                        amount = g['credits']
                    ok, res = group_red_packet_service.create_packet(
                        g['id'], g['owner_id'], amount, 5,
                        message='每日群福利', source_type='group_pool', packet_type='lucky'
                    )
                    if ok:
                        with db_cursor(commit=True) as cur:
                            cur.execute('UPDATE groups SET last_red_packet_date=? WHERE id=?', (today, g['id']))
                        print(f'[group-rp] group {g["id"]} sent {amount}')
                except Exception as e:
                    print(f'[group-rp] failed group {g["id"]}: {e}')
        except Exception as e:
            print(f'[group-rp] error: {e}')
        await asyncio.sleep(60)


'''
    c = c[:first] + new_block + c[end:]
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('done')