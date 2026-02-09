from __future__ import annotations

import os
import hmac
import bcrypt
from fastapi import Request
from fastapi.responses import RedirectResponse

def get_admin_user() -> str:
    return os.getenv("ADMIN_USER", "admin")

def get_admin_password() -> str:
    # Plaintext or bcrypt hash (starts with $2b$...)
    return os.getenv("ADMIN_PASSWORD", "change_me")

def verify_password(plain: str, stored: str) -> bool:
    stored = stored or ""
    plain = plain or ""
    try:
        if stored.startswith("$2"):
            return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
        return hmac.compare_digest(plain, stored)
    except Exception:
        return False

def is_admin(request: Request) -> bool:
    return bool(request.session.get("is_admin"))

def require_admin(request: Request):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None
