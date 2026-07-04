from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from backend.key_system import (
    validate_key, ban_key, unban_key, get_stock, get_all_keys, is_valid_key,
    generate_keys as gen_keys, redeem_key
)

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
ADMIN_KEY = "admin123"

app = FastAPI(title="License Key API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_admin(authorization: Optional[str] = Header(None)):
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


@app.post("/api/check")
async def api_check(req: ValidateRequest):
    valid = is_valid_key(req.key)
    return {"valid": valid, "message": "Key format valid" if valid else "Invalid key format"}


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
