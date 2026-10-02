p = 'core/services/group_resource_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

new_code = '''

async def call_agent_with_group_resource(group_id, user_id, agent_id, question):
    """群共享调用：检查配额 → 调模型 → 记使用"""
    from . import model_service
    # 检查配额
    ok, quota = check_quota(group_id, user_id, agent_id)
    if not ok:
        return False, quota
    # 查智能体配置（可能在群主名下，不在员工名下）
    with db_cursor() as cur:
        cur.execute("SELECT * FROM model_configs WHERE id=?", (agent_id,))
        row = cur.fetchone()
    if not row:
        return False, '智能体配置不存在'
    model_config = dict(row)
    # 调模型
    try:
        from .message.model_call import call_model_with_config
        reply = await call_model_with_config(model_config, question)
    except Exception as e:
        return False, f'模型调用失败：{e}'
    # 记使用
    record_usage(group_id, user_id, agent_id, agent_id)
    return True, reply
'''

if 'async def call_agent_with_group_resource' in c:
    print('already exists')
else:
    with open(p, 'a', encoding='utf-8') as f:
        f.write(new_code)
    print('appended OK')