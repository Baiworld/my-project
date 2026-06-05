"""FR-10 Email verification service — SMTP send + code verification"""

import random
import smtplib
from email.mime.text import MIMEText
from flask import current_app


def generate_verification_code() -> str:
    return f"{random.randint(100000, 999999)}"


def send_verification_email(email: str, code: str) -> bool:
    try:
        host = current_app.config.get("MAIL_SERVER", "smtp.example.com")
        port = current_app.config.get("MAIL_PORT", 587)
        username = current_app.config.get("MAIL_USERNAME", "")
        password = current_app.config.get("MAIL_PASSWORD", "")

        msg = MIMEText(
            f"Your verification code is: {code}\nThis code will expire in 10 minutes.",
            "plain", "utf-8",
        )
        msg["Subject"] = "Email Verification — Hybrid Recommendation System"
        msg["From"] = username or "noreply@recommend.local"
        msg["To"] = email

        if host == "smtp.example.com" or not username:
            # Dev mode — log code instead of sending
            current_app.logger.info(f"[DEV] Verification code for {email}: {code}")
            return True

        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {e}")
        return False
