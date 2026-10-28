"""Sends password-reset emails through SMTP (configured via environment variables)."""

import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def is_smtp_configured():
    """Return True when all required SMTP settings are present."""
    return all(os.getenv(key) for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def send_reset_code(to_email, code):
    """Email a password-reset code. Returns True on success, False otherwise."""
    if not is_smtp_configured():
        return False

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", user)

    message = EmailMessage()
    message["Subject"] = "Your password reset code"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        f"Your password reset code is: {code}\n\n"
        "It expires in 15 minutes. If you did not request this, you can ignore this email."
    )

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(message)
        return True
    except Exception:
        return False
