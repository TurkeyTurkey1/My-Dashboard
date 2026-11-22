from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import time
from typing import Any

from fastapi import Body, FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import ROOT, settings
from app.connectors.registry import collect

app = FastAPI(title="My Dashboard")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")

_cache: dict[str, Any] = {"ts": 0.0, "data": None}
_sessions: set[str] = set()
SESSION_COOKIE = "dashboard_session"


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    s = str(value)
    if len(s) <= 4:
        return "••••"
    return "••••••" + s[-2:]


def _read_env_lines(path):
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _write_env_updates(updates: dict[str, str | None]) -> None:
    path = ROOT / ".env"
    lines = _read_env_lines(path)
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if not m:
            out.append(line)
            continue
        key = m.group(1)
        if key in updates:
            seen.add(key)
            val = updates[key]
            if val is None:
                continue
            out.append(f"{key}={val}")
        else:
            out.append(line)
    for key, val in updates.items():
        if key in seen or val is None:
            continue
        out.append(f"{key}={val}")
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def _auth_enabled() -> bool:
    return bool(settings.dashboard_password)


def _expected_session_token() -> str:
    # Deterministic token based on secret+password so it survives restart; simple single-user gate.
    msg = f"dashboard:{settings.dashboard_password}".encode("utf-8")
    key = settings.session_secret.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def _is_authed(request: Request) -> bool:
    if not _auth_enabled():
        return True
    token = request.cookies.get(SESSION_COOKIE, "")
    return bool(token) and secrets.compare_digest(token, _expected_session_token())


def _require_auth(request: Request):
    if not _is_authed(request):
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    return None


@app.get("/login")
async def login_page(request: Request):
    if _is_authed(request):
        return RedirectResponse("/", status_code=302)
    return FileResponse(ROOT / "app" / "static" / "login.html")


@app.post("/api/login")
async def login(payload: dict[str, Any] = Body(...)):
    if not _auth_enabled():
        return JSONResponse({"ok": True})
    password = str(payload.get("password") or "")
    if not secrets.compare_digest(password, settings.dashboard_password):
        return JSONResponse({"detail": "Invalid password"}, status_code=401)
    resp = JSONResponse({"ok": True})
    secure = False  # Render/https can be handled by proxy; cookie still works. Set Secure via env later if needed.
    resp.set_cookie(SESSION_COOKIE, _expected_session_token(), httponly=True, samesite="lax", secure=secure, path="/")
    return resp


@app.post("/api/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@app.get("/")
async def index(request: Request):
    if not _is_authed(request):
        return RedirectResponse("/login", status_code=302)
    return FileResponse(ROOT / "app" / "static" / "index.html")


@app.get("/api/dashboard")
async def dashboard(request: Request, refresh: bool = Query(False)) -> Any:
    auth = _require_auth(request)
    if auth:
        return auth
    now = time.time()
    if not refresh and _cache["data"] is not None and (now - _cache["ts"]) < settings.cache_seconds:
        return _cache["data"]
    data = (await collect()).model_dump(mode="json")
    _cache["data"] = data
    _cache["ts"] = now
    return data


@app.get("/api/settings")
async def get_settings(request: Request) -> Any:
    auth = _require_auth(request)
    if auth:
        return auth
    accounts = []
    raw_accounts = settings.gmail_imap_accounts
    for i in range(3):
        acc = raw_accounts[i] if i < len(raw_accounts) else {}
        user = str(acc.get("user") or "")
        pwd = str(acc.get("app_password") or "")
        accounts.append({
            "user": user,
            "host": str(acc.get("host") or "imap.gmail.com"),
            "port": int(acc.get("port") or 993),
            "has_app_password": bool(pwd),
            "app_password_masked": _mask_secret(pwd),
        })
    return {
        "demo_mode": settings.demo_mode,
        "gmail_accounts": accounts,
        "seqta_mode": settings.seqta_mode,
        "auth_enabled": _auth_enabled(),
    }


@app.post("/api/settings")
async def save_settings(request: Request, payload: dict[str, Any] = Body(...)) -> JSONResponse:
    auth = _require_auth(request)
    if auth:
        return auth
    updates: dict[str, str | None] = {}

    demo_mode = payload.get("demo_mode")
    if isinstance(demo_mode, bool):
        updates["DEMO_MODE"] = "true" if demo_mode else "false"

    gmail_accounts = payload.get("gmail_accounts")
    if isinstance(gmail_accounts, list):
        slot_keys = [
            ("GMAIL_IMAP_USER", "GMAIL_IMAP_APP_PASSWORD"),
            ("GMAIL_IMAP_USER_2", "GMAIL_IMAP_APP_PASSWORD_2"),
            ("GMAIL_IMAP_USER_3", "GMAIL_IMAP_APP_PASSWORD_3"),
        ]
        existing = settings.gmail_imap_accounts
        for i, (uk, pk) in enumerate(slot_keys):
            acc = gmail_accounts[i] if i < len(gmail_accounts) and isinstance(gmail_accounts[i], dict) else {}
            user = str(acc.get("user") or "").strip()
            pwd_raw = acc.get("app_password")
            pwd = str(pwd_raw).strip() if pwd_raw is not None else ""
            keep_existing = bool(acc.get("keep_existing_password"))

            updates[uk] = user
            if pwd:
                updates[pk] = pwd.replace(" ", "")
            elif keep_existing and i < len(existing) and str(existing[i].get("app_password") or ""):
                updates[pk] = str(existing[i].get("app_password") or "")
            else:
                updates[pk] = ""
        updates["GMAIL_IMAP_ACCOUNTS"] = None
        updates["GMAIL_IMAP_HOST"] = str(payload.get("gmail_host") or "imap.gmail.com").strip() or "imap.gmail.com"
        updates["GMAIL_IMAP_PORT"] = str(int(payload.get("gmail_port") or 993))

    _write_env_updates(updates)
    settings.reload()
    _cache["data"] = None
    _cache["ts"] = 0.0
    return JSONResponse({"ok": True, "reloaded": True})


@app.post("/api/seqta/import")
async def import_seqta(request: Request, payload: Any = Body(...)) -> JSONResponse:
    auth = _require_auth(request)
    if auth:
        return auth
    path = settings.seqta_import_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    _cache["data"] = None
    _cache["ts"] = 0.0
    return JSONResponse({"ok": True, "saved": str(path)})
