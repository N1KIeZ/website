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
    validate_key, ban_key, unban_key, get_stock, get_all_keys,
    generate_keys as gen_keys, redeem_key
)
from backend.database import create_user, verify_user, get_user, init_db, get_db

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
ADMIN_KEY = os.environ.get("ADMIN_KEY", secrets.token_urlsafe(32))

USERS_FILE = BASE_DIR / "users.json"
JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_hex(32))
JWT_ALGO = "HS256"
JWT_EXPIRY_HOURS = 72

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="License Key API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"success": False, "message": "Rate limit exceeded. Try again later."})


# ─── Migrate existing JSON users to SQLite ──────────────────────
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


# ─── User storage (JSON fallback) ───────────────────────────────
def load_users():
    if USERS_FILE.exists():
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}


def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ─── JWT helpers ────────────────────────────────────────────────
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


# ─── Admin guard ────────────────────────────────────────────────
def verify_admin(authorization: Optional[str] = Header(None)):
    if authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return True


# ─── User guard ─────────────────────────────────────────────────
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization[7:]
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return username


# ─── Request models ─────────────────────────────────────────────
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


# ─── Auth endpoints ─────────────────────────────────────────────
@app.post("/api/register")
@limiter.limit("5/minute")
async def api_register(req: RegisterRequest, request: Request):
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
@limiter.limit("10/minute")
async def api_login(req: LoginRequest, request: Request):
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
@limiter.limit("10/minute")
async def api_login_key(req: LoginKeyRequest, request: Request):
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


# ─── Existing endpoints ─────────────────────────────────────────
@app.post("/api/validate")
async def api_validate(req: ValidateRequest):
    return validate_key(req.key, req.hwid)


@app.post("/api/generate")
async def api_generate(req: GenerateRequest, admin: bool = Depends(verify_admin)):
    if req.amount < 1 or req.amount > 1000:
        raise HTTPException(status_code=400, detail="Amount must be between 1 and 1000")
    return gen_keys(req.amount)


@app.get("/api/stock")
async def api_stock(admin: bool = Depends(verify_admin)):
    return get_stock()


@app.get("/api/keys")
async def api_keys(admin: bool = Depends(verify_admin)):
    return {"keys": get_all_keys()}


@app.post("/api/ban")
async def api_ban(req: BanRequest, admin: bool = Depends(verify_admin)):
    if ban_key(req.key):
        return {"success": True, "message": "Key banned"}
    return {"success": False, "message": "Key already banned"}


@app.post("/api/unban")
async def api_unban(req: BanRequest, admin: bool = Depends(verify_admin)):
    if unban_key(req.key):
        return {"success": True, "message": "Key unbanned"}
    return {"success": False, "message": "Key not banned"}


@app.post("/api/redeem")
async def api_redeem(req: ValidateRequest):
    return redeem_key(req.key)



@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


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
