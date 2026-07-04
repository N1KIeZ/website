import json
import random
import string
import os
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

BASE_DIR = Path(__file__).parent
KEYS_FILE = BASE_DIR / "keys.json"
BANNED_FILE = BASE_DIR / "banned.json"
ADMIN_KEY = "ADMIN-KEY-CHANGE-ME"

app = FastAPI(title="License Key API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_keys():
    if KEYS_FILE.exists():
        with open(KEYS_FILE, 'r') as f:
            return json.load(f)
    return {"available": [], "used": []}

def save_keys(data):
    with open(KEYS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_banned():
    if BANNED_FILE.exists():
        with open(BANNED_FILE, 'r') as f:
            return json.load(f)
    return []

def save_banned(data):
    with open(BANNED_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def gen_key():
    chars = string.ascii_uppercase + string.digits
    return f"KEY-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}"

def verify_admin_key(authorization: Optional[str] = Header(None)):
    if authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return True

class ValidateRequest(BaseModel):
    key: str
    hwid: Optional[str] = None

class GenerateRequest(BaseModel):
    amount: int = 1

class BanRequest(BaseModel):
    key: str

class KeyResponse(BaseModel):
    key: str
    created: str
    hwid: str = None
    activated_at: str = None
    status: str

@app.post("/api/validate", response_model=dict)
async def validate_key(request: ValidateRequest):
    key = request.key.strip().upper()
    hwid = request.hwid
    
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

@app.post("/api/generate", response_model=list)
async def generate_keys(request: GenerateRequest, admin: bool = Depends(verify_admin_key)):
    if request.amount < 1 or request.amount > 1000:
        raise HTTPException(status_code=400, detail="Amount must be between 1 and 1000")
    
    keys_data = load_keys()
    new_keys = []
    for _ in range(request.amount):
        key = gen_key()
        entry = {"key": key, "created": datetime.now().isoformat()}
        keys_data["available"].append(entry)
        new_keys.append(entry)
    save_keys(keys_data)
    return new_keys

@app.get("/api/stock")
async def get_stock(admin: bool = Depends(verify_admin_key)):
    keys_data = load_keys()
    banned = load_banned()
    return {
        "available": len(keys_data["available"]),
        "used": len(keys_data["used"]),
        "banned": len(banned)
    }

@app.post("/api/ban")
async def ban_key(request: BanRequest, admin: bool = Depends(verify_admin_key)):
    key = request.key.strip().upper()
    banned = load_banned()
    if key not in banned:
        banned.append(key)
        save_banned(banned)
        
        keys_data = load_keys()
        for i, k in enumerate(keys_data["available"]):
            if k["key"] == key:
                keys_data["available"].pop(i)
                break
        for i, k in enumerate(keys_data["used"]):
            if k["key"] == key:
                keys_data["used"].pop(i)
                break
        save_keys(keys_data)
        return {"success": True, "message": "Key banned"}
    return {"success": False, "message": "Key already banned"}

@app.post("/api/unban")
async def unban_key(request: BanRequest, admin: bool = Depends(verify_admin_key)):
    key = request.key.strip().upper()
    banned = load_banned()
    if key in banned:
        banned.remove(key)
        save_banned(banned)
        return {"success": True, "message": "Key unbanned"}
    return {"success": False, "message": "Key not banned"}

@app.get("/api/keys")
async def list_keys(admin: bool = Depends(verify_admin_key)):
    keys_data = load_keys()
    banned = load_banned()
    
    all_keys = []
    for k in keys_data["available"]:
        all_keys.append({**k, "status": "available"})
    for k in keys_data["used"]:
        all_keys.append({**k, "status": "used"})
    for k in banned:
        all_keys.append({"key": k, "status": "banned"})
    
    return {"keys": all_keys}

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)