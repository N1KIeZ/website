with open('backend/key_system.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
out = []
i = 0
while i < len(lines):
    line = lines[i]
    # First return: from available (line after save_keys)
    if 'return {"success": True, "message": "Key redeemed"}' in line and i < 255:
        out.append('            return {"success": True, "message": "Key redeemed", "duration": duration}')
        i += 1
        continue
    # The fallback section (not in DB)
    if 'activate it (for EXE-generated keys)' in line:
        out.append('    # Valid signature but not in DB - activate it (for offline-generated keys)')
        i += 1
        continue
    if line.strip().startswith('entry = {"key": key, "activated_at"'):
        out.append('    duration = _decode_duration(key)')
        out.append('    entry = {"key": key, "duration": duration, "activated_at": datetime.now().isoformat(), "redeemed": True}')
        i += 1
        continue
    # Second return: fallback case
    if 'return {"success": True, "message": "Key redeemed"}' in line and i > 255:
        out.append('    return {"success": True, "message": "Key redeemed", "duration": duration}')
        i += 1
        continue
    out.append(line)
    i += 1

with open('backend/key_system.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('Fixed')
