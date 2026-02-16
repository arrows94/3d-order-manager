import os
from typing import List
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from pathlib import Path

# Konfiguration laden
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM=os.getenv("MAIL_FROM", "noreply@localhost"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "localhost"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "True") == "True",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "False") == "True",
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_email_async(subject: str, email_to: str, body_html: str):
    """
    Sendet eine E-Mail asynchron im Hintergrund.
    """
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=body_html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
    except Exception as e:
        print(f"Fehler beim Senden der E-Mail: {e}")

# --- Templates für verschiedene Status ---

def get_new_order_html(customer_name: str, token: str, app_name: str) -> str:
    url = f"http://localhost:8080/r/{token}"  # Passe Domain ggf. über .env an
    return f"""
    <h3>Hallo {customer_name},</h3>
    <p>Danke für deinen Auftrag bei {app_name}!</p>
    <p>Du kannst den Status hier verfolgen:</p>
    <p><a href="{url}">{url}</a></p>
    <p>Wir melden uns, sobald wir den Auftrag geprüft haben.</p>
    """

def get_price_sent_html(customer_name: str, token: str, price_str: str) -> str:
    url = f"http://localhost:8080/r/{token}"
    return f"""
    <h3>Hallo {customer_name},</h3>
    <p>Gute Nachrichten: Wir haben deinen Auftrag geprüft.</p>
    <p><strong>Preisangebot: {price_str}</strong></p>
    <p>Bitte bestätige oder lehne das Angebot hier ab:</p>
    <p><a href="{url}">{url}</a></p>
    """

def get_completed_html(customer_name: str, token: str) -> str:
    url = f"http://localhost:8080/r/{token}"
    return f"""
    <h3>Auftrag erledigt!</h3>
    <p>Hallo {customer_name}, dein 3D-Druck ist fertig.</p>
    <p>Status prüfen: <a href="{url}">{url}</a></p>
    """
