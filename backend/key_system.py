import json
import os
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KEYS_FILE = BASE_DIR / "keys.json"
BANNED_FILE = BASE_DIR / "banned.json"
KEYS_DB_FILE = BASE_DIR / "keys_db.json"
BANNED_KEYS_FILE = BASE_DIR / "banned_keys.json"

_CH = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
PUBLIC_N = 59596791868544965917715049293139712060670803368525004046780554740535049298561
PUBLIC_E = 65537


def b32_decode(s):
    bits = ""
    for ch in s:
        val = _CH.find(ch)
        if val == -1:
            return None
        bits += f"{val:05b}"
    bytes_out = []
    for i in range(0, len(bits), 8):
        if i + 8 <= len(bits):
            bytes_out.append(int(bits[i:i+8], 2))
    return bytes_out


def bytes_to_int(b):
    return int.from_bytes(b, byteorder='big')


def _h(s):
    h = 0
    for c in s:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFFFFFFFFFF
    return h


def is_valid_key(key):
    if not key:
        return False
    clean = key.strip().upper().replace('-', '')
    if len(clean) < 15:
        return False
    payload = clean[:10]
    sig_str = clean[10:]
    sig_bytes = b32_decode(sig_str)
    if sig_bytes is None:
        return False
    sig = bytes_to_int(sig_bytes)
    decrypted = pow(sig, PUBLIC_E, PUBLIC_N)
    expected = _h(payload)
    return decrypted == expected


def _migrate_keys(data):
    if "available" in data and "used" in data:
        return data
    if "keys" in data:
        return {"available": [{"key": k} for k in data["keys"]], "used": []}
    if "active" in data:
        return {
            "available": [],
            "used": [k if isinstance(k, dict) else {"key": k} for k in data["active"]]
        }
    return {"available": [], "used": []}


def load_keys():
    if KEYS_FILE.exists():
        with open(KEYS_FILE, 'r') as f:
            return _migrate_keys(json.load(f))
    if KEYS_DB_FILE.exists():
        with open(KEYS_DB_FILE, 'r') as f:
            data = json.load(f)
            migrated = _migrate_keys(data)
            save_keys(migrated)
            return migrated
    return {"available": [], "used": []}


def save_keys(data):
    with open(KEYS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_banned():
    if BANNED_FILE.exists():
        with open(BANNED_FILE, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "banned" in data:
                return data["banned"]
            return []
    if BANNED_KEYS_FILE.exists():
        with open(BANNED_KEYS_FILE, 'r') as f:
            data = json.load(f)
            if isinstance(data, dict) and "banned" in data:
                return data["banned"]
    if KEYS_DB_FILE.exists():
        with open(KEYS_DB_FILE, 'r') as f:
            data = json.load(f)
            if "banned" in data:
                banned = [k["key"] if isinstance(k, dict) else k for k in data["banned"]]
                save_banned(banned)
                return banned
    return []


def save_banned(data):
    with open(BANNED_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def validate_key(key, hwid=None):
    key = key.strip().upper()
    banned = load_banned()
    if key in banned:
        return {"valid": False, "message": "Key is banned"}

    if not is_valid_key(key):
        return {"valid": False, "message": "Invalid key signature"}

    keys_data = load_keys()

    for i, k in enumerate(keys_data["available"]):
        if k["key"] == key:
            k["hwid"] = hwid
            k["activated_at"] = datetime.now().isoformat()
            keys_data["used"].append(k)
            del keys_data["available"][i]
            save_keys(keys_data)
            return {"valid": True, "message": "Key activated", "key": k}

    for k in keys_data["used"]:
        if k["key"] == key:
            if hwid and k.get("hwid") and k["hwid"] != hwid:
                return {"valid": False, "message": "Key locked to another device"}
            return {"valid": True, "message": "Key already active", "key": k}

    # Key has valid signature but isn't in DB ÔÇö activate on the fly
    entry = {"key": key, "hwid": hwid, "activated_at": datetime.now().isoformat()}
    keys_data["used"].append(entry)
    save_keys(keys_data)
    return {"valid": True, "message": "Key activated", "key": entry}


def ban_key(key):
    key = key.strip().upper()
    banned = load_banned()
    if key not in banned:
        banned.append(key)
        save_banned(banned)
        keys_data = load_keys()
        keys_data["available"] = [k for k in keys_data["available"] if k["key"] != key]
        keys_data["used"] = [k for k in keys_data["used"] if k["key"] != key]
        save_keys(keys_data)
        return True
    return False


def unban_key(key):
    key = key.strip().upper()
    banned = load_banned()
    if key in banned:
        banned.remove(key)
        save_banned(banned)
        return True
    return False


def get_stock():
    keys_data = load_keys()
    banned = load_banned()
    return {
        "available": len(keys_data["available"]),
        "used": len(keys_data["used"]),
        "banned": len(banned)
    }


def generate_keys(amount, duration='lifetime'):
    """Generate keys with an embedded duration and server-side expiry."""
    keys_data = load_keys()
    new_keys = []

    STATIC_D = 44411372526603278231981439147021640563272121446936530565914521287135611291649
    STATIC_N = 59596791868544965917715049293139712060670803368525004046780554740535049298561
    prefix_chars = _CH[:-3]

    def b32_encode(data):
        bits = "".join(f"{b:08b}" for b in data)
        padding = (5 - len(bits) % 5) % 5
        bits += "0" * padding
        return "".join(_CH[int(bits[i:i+5], 2)] for i in range(0, len(bits), 5))

    existing = set()
    for k in keys_data["available"]:
        existing.add(k["key"])
    for k in keys_data["used"]:
        existing.add(k["key"])
    for k in load_banned():
        existing.add(k)

    dur_char, td = _DURATION_MAP.get(duration, ('L', None))
    expires_at = (datetime.now() + td).isoformat() if td else None

    while len(new_keys) < amount:
        prefix = "".join(secrets.choice(prefix_chars) for _ in range(9))
        payload = prefix + dur_char
        h = _h(payload)
        sig = pow(h, STATIC_D, STATIC_N)
        sig_bytes = sig.to_bytes((sig.bit_length() + 7) // 8, byteorder='big')
        sig_b32 = b32_encode(sig_bytes)
        raw_key = payload + sig_b32
        formatted_key = "-".join(raw_key[i:i+5] for i in range(0, len(raw_key), 5))

        if formatted_key not in existing:
            existing.add(formatted_key)
            entry = {
                "key": formatted_key,
                "duration": duration,
                "expires_at": expires_at,
                "created": datetime.now().isoformat(),
            }
            keys_data["available"].append(entry)
            new_keys.append(entry)

    save_keys(keys_data)
    return new_keys


def redeem_key(key):
    """Redeem a key for registration. Only works if key is available (not yet used)."""
    key = key.strip().upper()
    banned = load_banned()
    if key in banned:
        return {"success": False, "message": "Key is banned"}

    if not is_valid_key(key):
        return {"success": False, "message": "Invalid key signature"}

    keys_data = load_keys()

    # Check if already used
    for k in keys_data["used"]:
        if k["key"] == key:
            return {"success": False, "message": "Key already redeemed"}

    # Find and consume from available
    for i, k in enumerate(keys_data["available"]):
        if k["key"] == key:
            duration = k.get("duration") or _decode_duration(key)
            entry = {**k, "activated_at": datetime.now().isoformat(), "redeemed": True}
            keys_data["used"].append(entry)
            del keys_data["available"][i]
            save_keys(keys_data)
            return {"success": True, "message": "Key redeemed", "duration": duration}

    # Valid signature but not in DB - activate it (for offline-generated keys)
    duration = _decode_duration(key)
    entry = {"key": key, "duration": duration, "activated_at": datetime.now().isoformat(), "redeemed": True}
    keys_data["used"].append(entry)
    save_keys(keys_data)
    return {"success": True, "message": "Key redeemed", "duration": duration}


_DURATION_MAP = {
    '5 minutes': ('H', timedelta(minutes=5)),
    '30 minutes': ('T', timedelta(minutes=30)),
    '1 hour': ('U', timedelta(hours=1)),
    '1 day': ('D', timedelta(days=1)),
    '1 week': ('W', timedelta(days=7)),
    '1 month': ('M', timedelta(days=30)),
    '1 year': ('Y', timedelta(days=365)),
    'lifetime': ('L', None),
}

_DUR_CHAR_TO_NAME = {v[0]: k for k, v in _DURATION_MAP.items()}

# Shorthand aliases used by the Discord bot
DURATION_ALIASES = {
    '5m': '5 minutes',
    '30m': '30 minutes',
    '1h': '1 hour',
    'hour': '1 hour',
    'day': '1 day',
    '1d': '1 day',
    'week': '1 week',
    '1w': '1 week',
    'month': '1 month',
    '1mo': '1 month',
    'year': '1 year',
    '1y': '1 year',
    'lifetime': 'lifetime',
    'perm': 'lifetime',
    'permament': 'lifetime',
    'forever': 'lifetime',
}


def resolve_duration(raw):
    """Resolve a user-supplied duration string to the canonical form."""
    raw = raw.strip().lower()
    if raw in DURATION_ALIASES:
        return DURATION_ALIASES[raw]
    if raw in _DURATION_MAP:
        return raw
    return 'lifetime'


def _decode_duration(key):
    """Extract duration info from the key payload itself (character 9 in raw format)."""
    clean = key.strip().upper().replace('-', '')
    if len(clean) < 10:
        return 'lifetime'
    dur_char = clean[9]
    return _DUR_CHAR_TO_NAME.get(dur_char, 'lifetime')


def _duration_to_expiry(duration):
    """Convert a duration string to an ISO expiry datetime string, or None for lifetime."""
    if duration == 'lifetime' or not duration:
        return None
    now = datetime.now()
    td = _DURATION_MAP.get(duration, (None, None))[1]
    if td is None:
        return None
    return (now + td).isoformat()


def _key_is_expired(key_entry):
    """Return True if a key entry has passed its expiry."""
    exp = key_entry.get('expires_at')
    if not exp:
        return False
    try:
        return datetime.fromisoformat(exp) < datetime.now()
    except Exception:
        return False


def get_all_keys():
    keys_data = load_keys()
    banned = load_banned()
    all_keys = []
    for k in keys_data["available"]:
        all_keys.append({**k, "status": "available"})
    for k in keys_data["used"]:
        all_keys.append({**k, "status": "used"})
    for k in banned:
        all_keys.append({"key": k, "status": "banned"})
    return all_keys
