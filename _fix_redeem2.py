with open('backend/key_system.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '        if k["key"] == key:\n            entry = {**k'
new = '        if k["key"] == key:\n            duration = k.get("duration") or _decode_duration(key)\n            entry = {**k'

if old in content:
    content = content.replace(old, new)
    with open('backend/key_system.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed')
else:
    print('Pattern not found')
