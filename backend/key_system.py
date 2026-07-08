import json
import os
import secrets
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KEYS_FILE = BASE_DIR / "keys.json"
BANNED_FILE = BASE_DIR / "banned.json"


def _format_key(raw: str) -> str:
    """XXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX"""
    return f"{raw[:4]}-{raw[4:12]}-{raw[12:20]}-{raw[20:28]}"


def _key_exists(key: str, keys_data: dict) -> bool:
    for k in keys_data.get("available", []):
        if k["key"] == key:
            return True
    for k in keys_data.get("used", []):
        if k["key"] == key:
            return True
    return False


def load_keys():
    if KEYS_FILE.exists():
        with open(KEYS_FILE, 'r') as f:
            data = json.load(f)
        if "available" not in data:
            data = {"available": [], "used": []}
        return data
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


def save_banned(data):
    with open(BANNED_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def generate_keys(amount):
    keys_data = load_keys()
    new_keys = []

    existing = set()
    for k in keys_data["available"]:
        existing.add(k["key"])
    for k in keys_data["used"]:
        existing.add(k["key"])
    for k in load_banned():
        existing.add(k)

    while len(new_keys) < amount:
        raw = secrets.token_hex(16).upper()
        formatted = _format_key(raw)
        if formatted not in existing:
            existing.add(formatted)
            entry = {"key": formatted, "created": datetime.now().isoformat()}
            keys_data["available"].append(entry)
            new_keys.append(entry)

    save_keys(keys_data)
    return new_keys


def validate_key(key, hwid=None):
    key = key.strip().upper()
    banned = load_banned()
    if key in banned:
        return {"valid": False, "message": "Key is banned"}

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

    return {"valid": False, "message": "Key not found"}


def redeem_key(key):
    key = key.strip().upper()
    banned = load_banned()
    if key in banned:
        return {"success": False, "message": "Key is banned"}

    keys_data = load_keys()

    for k in keys_data["used"]:
        if k["key"] == key:
            return {"success": False, "message": "Key already redeemed"}

    for i, k in enumerate(keys_data["available"]):
        if k["key"] == key:
            entry = {**k, "activated_at": datetime.now().isoformat(), "redeemed": True}
            keys_data["used"].append(entry)
            del keys_data["available"][i]
            save_keys(keys_data)
            return {"success": True, "message": "Key redeemed"}

    return {"success": False, "message": "Key not found"}


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
