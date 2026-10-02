p = 'static/modules/group_chat.js'
with open(p, encoding='utf-8') as f:
    c = f.read()

# 定位领取成功的调用：在 claim 接口调用之后的 window.openGroupRedPacket
marker = "const resp = await fetch('/group/red-packets/' + packetId + '/claim'"
idx = c.find(marker)
if idx < 0:
    print('marker not found')
else:
    # 从 marker 之后找 window.openGroupRedPacket(packetId);
    target = 'window.openGroupRedPacket(packetId);'
    sub = c.find(target, idx)
    if sub < 0:
        print('target not found')
    else:
        # 检查前面是否已经有 toast 调用
        before = c[:sub]
        if 'showGroupToast' in before[-200:]:
            print('already inserted')
        else:
            toast_code = "if (window.showGroupToast) window.showGroupToast('🧧 你抢到了 ' + data.amount + ' 积分');\n            "
            c = c[:sub] + toast_code + c[sub:]
            with open(p, 'w', encoding='utf-8') as f:
                f.write(c)
            print('inserted OK')