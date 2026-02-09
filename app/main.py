from __future__ import annotations

import os
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, UploadFile, File, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlmodel import select

from .db import init_db, session_scope
from .models import Order, OrderStatus
from .auth import get_admin_user, get_admin_password, verify_password, is_admin, require_admin

APP_NAME = os.getenv("SITE_NAME", "3D Auftragsmanager")
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "EUR")

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=APP_NAME)
app.state.max_upload_mb = MAX_UPLOAD_MB

# Sessions
session_secret = os.getenv("SESSION_SECRET", "change_me_to_a_long_random_string")
app.add_middleware(SessionMiddleware, secret_key=session_secret, same_site="lax", https_only=False)

# Static
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

def _now():
    return datetime.utcnow()

def _format_price(price_cents: Optional[int], currency: str) -> Optional[str]:
    if price_cents is None:
        return None
    euros = price_cents / 100.0
    if currency.upper() == "EUR":
        return f"{euros:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{euros:,.2f} {currency}"

def _safe_filename(name: str) -> str:
    name = name.strip().replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name[:120] or "upload.bin"

def _validate_upload(upload: UploadFile) -> None:
    # Basic checks. You can tighten these later.
    allowed = {"image/png", "image/jpeg", "image/webp", "image/gif"}
    if upload.content_type not in allowed:
        raise ValueError("Bitte nur Bilder hochladen (png/jpg/webp/gif).")

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "app_name": APP_NAME,
    })

@app.post("/submit")
async def submit(
    request: Request,
    customer_name: str = Form(...),
    customer_email: str = Form(...),
    description: str = Form(...),
    model_link: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
):
    token = secrets.token_urlsafe(18)  # ~24 chars
    rel_image_path = None

    if image and image.filename:
        _validate_upload(image)

        # size check
        content = await image.read()
        if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "app_name": APP_NAME,
                "error": f"Bild ist zu groß. Maximal {MAX_UPLOAD_MB} MB.",
            }, status_code=400)

        target_dir = UPLOAD_DIR / token
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = _safe_filename(image.filename)
        target_file = target_dir / filename
        target_file.write_bytes(content)
        rel_image_path = f"uploads/{token}/{filename}"

    with session_scope() as session:
        order = Order(
            token=token,
            customer_name=customer_name.strip(),
            customer_email=customer_email.strip(),
            description=description.strip(),
            model_link=(model_link.strip() if model_link else None),
            image_path=rel_image_path,
            status=OrderStatus.NEW,
            currency=DEFAULT_CURRENCY,
        )
        session.add(order)
        session.commit()
        session.refresh(order)

    return templates.TemplateResponse("submit_success.html", {
        "request": request,
        "app_name": APP_NAME,
        "token": token,
    })

@app.get("/r/{token}", response_class=HTMLResponse)
def request_public(request: Request, token: str):
    with session_scope() as session:
        order = session.exec(select(Order).where(Order.token == token)).first()

    if not order:
        return templates.TemplateResponse("request_public.html", {
            "request": request,
            "app_name": APP_NAME,
            "not_found": True,
        }, status_code=404)

    price_str = _format_price(order.price_cents, order.currency)
    return templates.TemplateResponse("request_public.html", {
        "request": request,
        "app_name": APP_NAME,
        "order": order,
        "price_str": price_str,
    })

@app.post("/r/{token}/decision")
def customer_decision(
    request: Request,
    token: str,
    decision: str = Form(...),
    note: Optional[str] = Form(None),
):
    decision = (decision or "").lower()
    with session_scope() as session:
        order = session.exec(select(Order).where(Order.token == token)).first()
        if not order:
            return RedirectResponse(url=f"/r/{token}", status_code=303)

        if order.status != OrderStatus.PRICE_SENT:
            return RedirectResponse(url=f"/r/{token}", status_code=303)

        if decision == "accept":
            order.status = OrderStatus.PRICE_ACCEPTED
        else:
            order.status = OrderStatus.PRICE_REJECTED

        order.customer_decision_note = (note.strip() if note else None)
        order.updated_at = _now()
        session.add(order)
        session.commit()

    return RedirectResponse(url=f"/r/{token}", status_code=303)

@app.get("/uploads/{token}/{filename}")
def get_upload(request: Request, token: str, filename: str):
    filename = _safe_filename(filename)
    with session_scope() as session:
        order = session.exec(select(Order).where(Order.token == token)).first()

    if not order or not order.image_path:
        return RedirectResponse(url="/", status_code=303)

    # Ensure requested file matches stored path
    expected = f"uploads/{token}/{filename}"
    if order.image_path != expected:
        return RedirectResponse(url="/", status_code=303)

    file_path = DATA_DIR / expected
    if not file_path.exists():
        return RedirectResponse(url="/", status_code=303)

    # Allow if admin or if user has the token (which is in URL anyway)
    return FileResponse(str(file_path))

# ---------------- Admin ----------------

@app.get("/admin/login", response_class=HTMLResponse)
def admin_login(request: Request):
    return templates.TemplateResponse("admin_login.html", {
        "request": request,
        "app_name": APP_NAME,
        "admin_user": get_admin_user(),
    })

@app.post("/admin/login")
def admin_login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if username == get_admin_user() and verify_password(password, get_admin_password()):
        request.session["is_admin"] = True
        return RedirectResponse(url="/admin", status_code=303)

    return templates.TemplateResponse("admin_login.html", {
        "request": request,
        "app_name": APP_NAME,
        "admin_user": get_admin_user(),
        "error": "Login fehlgeschlagen.",
    }, status_code=401)

@app.post("/admin/logout")
def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, q: Optional[str] = None, status_filter: Optional[str] = None):
    redir = require_admin(request)
    if redir:
        return redir

    with session_scope() as session:
        stmt = select(Order).order_by(Order.created_at.desc())
        orders = list(session.exec(stmt))

    # simple filtering (in-memory; fine for small)
    if status_filter:
        orders = [o for o in orders if o.status.value == status_filter]
    if q:
        ql = q.lower()
        orders = [o for o in orders if ql in o.customer_name.lower() or ql in o.customer_email.lower() or (o.model_link or "").lower().find(ql) >= 0]

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "app_name": APP_NAME,
        "orders": orders,
        "q": q or "",
        "status_filter": status_filter or "",
        "statuses": [s.value for s in OrderStatus],
        "is_admin": True,
    })

@app.get("/admin/order/{order_id}", response_class=HTMLResponse)
def admin_order(request: Request, order_id: int):
    redir = require_admin(request)
    if redir:
        return redir

    with session_scope() as session:
        order = session.get(Order, order_id)

    if not order:
        return RedirectResponse(url="/admin", status_code=303)

    price_str = _format_price(order.price_cents, order.currency)
    return templates.TemplateResponse("admin_request.html", {
        "request": request,
        "app_name": APP_NAME,
        "order": order,
        "price_str": price_str,
        "statuses": [s.value for s in OrderStatus],
        "is_admin": True,
    })

@app.post("/admin/order/{order_id}/reject")
def admin_reject(
    request: Request,
    order_id: int,
    admin_note: Optional[str] = Form(None),
):
    redir = require_admin(request)
    if redir:
        return redir

    with session_scope() as session:
        order = session.get(Order, order_id)
        if not order:
            return RedirectResponse(url="/admin", status_code=303)
        order.status = OrderStatus.REJECTED
        order.admin_note = (admin_note.strip() if admin_note else None)
        order.updated_at = _now()
        session.add(order)
        session.commit()

    return RedirectResponse(url=f"/admin/order/{order_id}", status_code=303)

@app.post("/admin/order/{order_id}/accept")
def admin_accept(
    request: Request,
    order_id: int,
    admin_note: Optional[str] = Form(None),
):
    redir = require_admin(request)
    if redir:
        return redir

    with session_scope() as session:
        order = session.get(Order, order_id)
        if not order:
            return RedirectResponse(url="/admin", status_code=303)
        # Accept only makes sense from NEW or PRICE_REJECTED maybe.
        if order.status in {OrderStatus.NEW, OrderStatus.PRICE_REJECTED}:
            order.status = OrderStatus.AWAITING_PRICE
        order.admin_note = (admin_note.strip() if admin_note else order.admin_note)
        order.updated_at = _now()
        session.add(order)
        session.commit()

    return RedirectResponse(url=f"/admin/order/{order_id}", status_code=303)

@app.post("/admin/order/{order_id}/set_price")
def admin_set_price(
    request: Request,
    order_id: int,
    price_eur: str = Form(...),
):
    redir = require_admin(request)
    if redir:
        return redir

    # parse price like "12,50" or "12.50"
    cleaned = (price_eur or "").strip().replace(" ", "").replace(",", ".")
    try:
        value = float(cleaned)
        if value < 0:
            raise ValueError
    except Exception:
        return RedirectResponse(url=f"/admin/order/{order_id}", status_code=303)

    cents = int(round(value * 100))

    with session_scope() as session:
        order = session.get(Order, order_id)
        if not order:
            return RedirectResponse(url="/admin", status_code=303)
        order.price_cents = cents
        order.currency = DEFAULT_CURRENCY
        order.status = OrderStatus.PRICE_SENT
        order.updated_at = _now()
        session.add(order)
        session.commit()

    return RedirectResponse(url=f"/admin/order/{order_id}", status_code=303)

@app.post("/admin/order/{order_id}/complete")
def admin_complete(request: Request, order_id: int):
    redir = require_admin(request)
    if redir:
        return redir

    with session_scope() as session:
        order = session.get(Order, order_id)
        if not order:
            return RedirectResponse(url="/admin", status_code=303)
        # Only complete if price accepted (or you can relax it)
        if order.status == OrderStatus.PRICE_ACCEPTED:
            order.status = OrderStatus.COMPLETED
            order.updated_at = _now()
            session.add(order)
            session.commit()

    return RedirectResponse(url=f"/admin/order/{order_id}", status_code=303)
