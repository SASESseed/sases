p = 'core/services/group_red_packet_service.py'
with open(p, encoding='utf-8') as f:
    c = f.read()

old = """    if remaining_count == 1:
        amount = round(remaining_amount, 2)
    else:
        max_amt = remaining_amount / remaining_count * 2
        amount = round(random.uniform(0.01, max_amt - 0.01), 2)
        if amount < 0.01:
            amount = 0.01
        if amount > remaining_amount - 0.01 * (remaining_count - 1):
            amount = round(remaining_amount - 0.01 * (remaining_count - 1), 2)"""

new = """    _ptype = 'lucky'
    try:
        _ptype = p['packet_type'] or 'lucky'
    except (KeyError, IndexError):
        _ptype = 'lucky'
    if remaining_count == 1:
        amount = round(remaining_amount, 2)
    elif _ptype == 'normal':
        amount = round(float(p['total_amount']) / int(p['total_count']), 2)
        if amount > remaining_amount:
            amount = round(remaining_amount, 2)
    else:
        max_amt = remaining_amount / remaining_count * 2
        amount = round(random.uniform(0.01, max_amt - 0.01), 2)
        if amount < 0.01:
            amount = 0.01
        if amount > remaining_amount - 0.01 * (remaining_count - 1):
            amount = round(remaining_amount - 0.01 * (remaining_count - 1), 2)"""

if old in c:
    c = c.replace(old, new)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('replaced OK')
else:
    print('old block NOT FOUND')