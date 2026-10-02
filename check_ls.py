import re
c = open('static/modules/group_chat.js', encoding='utf-8').read()
matches = re.findall(r'localStorage\.(?:get|set)Item\([^)]+\)', c)
for m in matches:
    print(m)