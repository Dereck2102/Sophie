from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

settings = get_settings()


class EmailDeliveryError(RuntimeError):
    pass


def send_email_message(to_email: str, subject: str, text_body: str) -> None:
    if not settings.SMTP_HOST:
        raise EmailDeliveryError("SMTP no configurado")

    message = EmailMessage()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(text_body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    except Exception as exc:  # pragma: no cover - depends on external SMTP
        raise EmailDeliveryError(str(exc)) from exc


def send_mfa_email_code(to_email: str, code: str, expires_minutes: int) -> None:
    subject = "Código de verificación MFA - SOPHIE"
    text_body = (
        "Tu código de verificación para iniciar sesión en SOPHIE es: "
        f"{code}\n\n"
        f"Este código expira en {expires_minutes} minutos. "
        "Si no intentaste iniciar sesión, ignora este mensaje."
    )
    send_email_message(to_email=to_email, subject=subject, text_body=text_body)
