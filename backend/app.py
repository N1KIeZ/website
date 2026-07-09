import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from backend.key_system import (
    validate_key, ban_key, unban_key, get_stock, get_all_keys, is_valid_key,
    generate_keys as gen_keys, redeem_key, _duration_to_expiry, _key_is_expired,
    resolve_duration, load_keys, save_keys, load_banned
)
from backend.database import create_user, verify_user, get_user, init_db, get_db, set_subscription_expiry

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"

USERS_FILE = BASE_DIR / "users.json"
JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_hex(32))
JWT_ALGO = "HS256"
JWT_EXPIRY_HOURS = 72

app = FastAPI(title="License Key API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ÔöÇÔöÇÔöÇ Migrate existing JSON users to SQLite ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def migrate_json_users():
    if not USERS_FILE.exists():
        return
    try:
        with open(USERS_FILE) as f:
            json_users = json.load(f)
    except (json.JSONDecodeError, IOError):
        return

    conn = get_db()
    cursor = conn.cursor()
    migrated = 0
    for username, data in json_users.items():
        if get_user(username):
            continue
        password = data.get("password", "")
        email = data.get("email", "")
        key = data.get("key", "")
        joined = data.get("joined", datetime.now(timezone.utc).isoformat())
        try:
            cursor.execute(
                'INSERT INTO users (username, password, email, created_at) VALUES (?, ?, ?, ?)',
                (username, password, email, joined)
            )
            migrated += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    if migrated > 0:
        print(f"Migrated {migrated} users from users.json to SQLite")

import sqlite3
migrate_json_users()


# ÔöÇÔöÇÔöÇ User storage (JSON fallback) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def load_users():
    if USERS_FILE.exists():
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}


def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ÔöÇÔöÇÔöÇ JWT helpers ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def create_token(username):
    payload = {
        "sub": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def verify_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload["sub"]
    except jwt.InvalidTokenError:
        return None



# ÔöÇÔöÇÔöÇ User guard ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization[7:]
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return username


# ÔöÇÔöÇÔöÇ Request models ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
class ValidateRequest(BaseModel):
    key: str
    hwid: Optional[str] = None


class GenerateRequest(BaseModel):
    amount: int = 1


class BanRequest(BaseModel):
    key: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    key: str


class LoginRequest(BaseModel):
    username: str
    password: str
    hwid: Optional[str] = None


class LoginKeyRequest(BaseModel):
    username: str
    key: str


BOT_SECRET = os.environ.get("BOT_SECRET", "CHANGE_ME_TO_A_RANDOM_STRING")
import logging
logger = logging.getLogger("uvicorn")
logger.warning(f"BOT_SECRET loaded: len={len(BOT_SECRET)}, prefix={BOT_SECRET[:4]}...")


class BotGenKeyRequest(BaseModel):
    duration: str = "lifetime"
    amount: int = 1
    secret: str


class BotVerifyRequest(BaseModel):
    key: str
    secret: str


class BotRevokeRequest(BaseModel):
    key: str
    secret: str


class LoaderVerifyRequest(BaseModel):
    key: str
    hwid: Optional[str] = None


# ÔöÇÔöÇÔöÇ Auth endpoints ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
@app.post("/api/register")
async def api_register(req: RegisterRequest):
    user = req.username.strip().lower()
    if not user or len(user) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")

    # Check if user exists in SQLite
    if get_user(user):
        raise HTTPException(status_code=409, detail="Username already taken")

    # Redeem the key on the server (one-time check)
    result = redeem_key(req.key.strip().upper())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # Create user in SQLite with bcrypt
    ok = create_user(user, req.password.strip())
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to create user")

    # Set subscription expiry based on key duration
    duration = result.get("duration", "lifetime")
    expiry = _duration_to_expiry(duration)
    set_subscription_expiry(user, expiry)

    # Also save to JSON for backward compatibility
    users = load_users()
    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    users[user] = {
        "username": req.username.strip(),
        "password": hashed,
        "key": req.key.strip().upper(),
        "joined": datetime.now(timezone.utc).isoformat(),
    }
    save_users(users)

    token = create_token(user)
    return {"success": True, "token": token, "user": {"username": user, "created_at": datetime.now(timezone.utc).isoformat()}}


@app.post("/api/login")
async def api_login(req: LoginRequest):
    """Login with username and password (SQLite database with bcrypt)"""
    username = req.username.strip().lower()
    result = verify_user(username, req.password.strip(), req.hwid)
    if result["success"]:
        token = create_token(username)
        user_data = result.get("user", {})
        return {
            "success": True,
            "token": token,
            "user": {
                "username": user_data.get("username", username),
                "email": user_data.get("email", ""),
                "subscription_expiry": user_data.get("subscription_expiry", ""),
                "created_at": user_data.get("created_at", ""),
                "is_banned": user_data.get("is_banned", 0)
            }
        }
    return result


@app.post("/api/login-key")
async def api_login_key(req: LoginKeyRequest):
    """Login with username and license key (for loader)"""
    user = req.username.strip().lower()
    key = req.key.strip().upper()

    # Validate the key
    result = validate_key(key)
    if not result.get("valid"):
        return {"success": False, "message": result.get("message", "Invalid license key")}

    # Check if user exists in SQLite
    db_user = get_user(user)
    if db_user:
        token = create_token(user)
        return {"success": True, "token": token, "user": db_user}

    # Fallback to JSON users
    users = load_users()
    if user in users:
        token = create_token(user)
        return {"success": True, "token": token, "user": users[user]}

    return {"success": False, "message": "User not found"}


@app.get("/api/session")
async def api_session(username: str = Depends(get_current_user)):
    return {"success": True, "user": {"username": username}}


# ÔöÇÔöÇÔöÇ Existing endpoints ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
@app.post("/api/validate")
async def api_validate(req: ValidateRequest):
    return validate_key(req.key, req.hwid)


@app.post("/api/generate")
async def api_generate(req: ValidateRequest):
    return {"detail": "Use /api/bot/genkey instead"}

@app.get("/api/stock")
async def api_stock():
    return get_stock()

@app.get("/api/keys")
async def api_keys():
    return {"keys": get_all_keys()}

@app.post("/api/ban")
async def api_ban(req: BanRequest):
    return {"success": ban_key(req.key)}

@app.post("/api/unban")
async def api_unban(req: BanRequest):
    return {"success": unban_key(req.key)}

@app.post("/api/redeem")
async def api_redeem(req: ValidateRequest):
    return redeem_key(req.key)


@app.post("/api/check")
async def api_check(req: ValidateRequest):
    valid = is_valid_key(req.key)
    return {"valid": valid, "message": "Key format valid" if valid else "Invalid key format"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.1.0"}


# ---------- Bot API endpoints ----------

@app.post("/api/bot/genkey")
async def api_bot_genkey(req: BotGenKeyRequest):
    """Generate license keys. Called by the Discord bot."""
    logger.warning(f"genkey secret check: got_len={len(req.secret)}, expected_len={len(BOT_SECRET)}, match={req.secret == BOT_SECRET}")
    if req.secret != BOT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid bot secret")
    if req.amount < 1 or req.amount > 50:
        raise HTTPException(status_code=400, detail="Amount must be 1-50")

    duration = resolve_duration(req.duration)
    new_keys = gen_keys(req.amount, duration)
    return {
        "success": True,
        "keys": [
            {
                "key": k["key"],
                "duration": k.get("duration", duration),
                "expires_at": k.get("expires_at"),
            }
            for k in new_keys
        ],
    }


@app.post("/api/bot/verify")
async def api_bot_verify(req: BotVerifyRequest):
    """Verify a key's validity. Called by the Discord bot."""
    if req.secret != BOT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid bot secret")

    key = req.key.strip().upper()
    banned = load_banned()
    if key in banned:
        return {"valid": False, "status": "banned", "message": "Key is banned"}

    if not is_valid_key(key):
        return {"valid": False, "status": "invalid", "message": "Invalid key signature"}

    keys_data = load_keys()
    for k in keys_data["available"]:
        if k["key"] == key:
            if _key_is_expired(k):
                return {"valid": False, "status": "expired", "message": "Key has expired",
                        "expires_at": k.get("expires_at"), "duration": k.get("duration", "lifetime")}
            return {"valid": True, "status": "available", "message": "Key is valid (unused)",
                    "duration": k.get("duration", "lifetime"), "expires_at": k.get("expires_at")}

    for k in keys_data["used"]:
        if k["key"] == key:
            if _key_is_expired(k):
                return {"valid": False, "status": "expired", "message": "Key has expired",
                        "expires_at": k.get("expires_at"), "duration": k.get("duration", "lifetime")}
            return {"valid": True, "status": "active", "message": "Key is active",
                    "duration": k.get("duration", "lifetime"), "expires_at": k.get("expires_at"),
                    "hwid": k.get("hwid"), "activated_at": k.get("activated_at")}

    return {"valid": False, "status": "not_found", "message": "Key not found in database"}


@app.post("/api/bot/revoke")
async def api_bot_revoke(req: BotRevokeRequest):
    """Revoke (ban) a key. Called by the Discord bot."""
    if req.secret != BOT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid bot secret")

    key = req.key.strip().upper()
    result = ban_key(key)
    if result:
        return {"success": True, "message": "Key revoked"}
    return {"success": False, "message": "Key not found or already banned"}


# ---------- Loader API endpoint ----------

@app.post("/api/loader/verify")
async def api_loader_verify(req: LoaderVerifyRequest):
    """Verify a key for the C++ loader. Returns validity + expiry info."""
    key = req.key.strip().upper()
    banned = load_banned()

    if key in banned:
        return {"success": False, "valid": False, "message": "Key is banned"}

    if not is_valid_key(key):
        return {"success": False, "valid": False, "message": "Invalid key"}

    keys_data = load_keys()

    # Check available keys
    for k in keys_data["available"]:
        if k["key"] == key:
            if _key_is_expired(k):
                return {"success": False, "valid": False, "message": "Key expired",
                        "expires_at": k.get("expires_at"), "duration": k.get("duration", "lifetime")}
            # Activate the key
            k["hwid"] = req.hwid
            k["activated_at"] = datetime.now(timezone.utc).isoformat()
            keys_data["used"].append(k)
            keys_data["available"].remove(k)
            save_keys(keys_data)
            return {
                "success": True, "valid": True, "message": "Key activated",
                "duration": k.get("duration", "lifetime"),
                "expires_at": k.get("expires_at"),
            }

    # Check used/active keys
    for k in keys_data["used"]:
        if k["key"] == key:
            if _key_is_expired(k):
                return {"success": False, "valid": False, "message": "Key expired",
                        "expires_at": k.get("expires_at"), "duration": k.get("duration", "lifetime")}
            # HWID check (optional - allow first 5 chars or exact match)
            if req.hwid and k.get("hwid") and k["hwid"] != req.hwid:
                return {"success": False, "valid": False, "message": "Key bound to another device"}
            return {
                "success": True, "valid": True, "message": "Key valid",
                "duration": k.get("duration", "lifetime"),
                "expires_at": k.get("expires_at"),
            }

    # Valid signature but not in DB - activate on the fly
    duration = _decode_duration(key)
    expires_at = _duration_to_expiry(duration)
    entry = {
        "key": key, "duration": duration, "expires_at": expires_at,
        "hwid": req.hwid, "activated_at": datetime.now(timezone.utc).isoformat(),
    }
    keys_data["used"].append(entry)
    save_keys(keys_data)
    return {
        "success": True, "valid": True, "message": "Key activated",
        "duration": duration, "expires_at": expires_at,
    }


MIME_TYPES = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".json": "application/json",
}


@app.get("/{path:path}")
async def serve_static(path: str):
    if not path:
        path = "index.html"
    full_path = PUBLIC_DIR / path
    if full_path.exists() and full_path.is_file():
        suffix = full_path.suffix.lower()
        media_type = MIME_TYPES.get(suffix, "application/octet-stream")
        return FileResponse(str(full_path), media_type=media_type)
    if not path.startswith("api/"):
        idx = PUBLIC_DIR / "index.html"
        if idx.exists():
            return FileResponse(str(idx))
    return JSONResponse(status_code=404, content={"detail": "Not found"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
