from __future__ import annotations

from app.core.config import get_settings

settings = get_settings()


class SmsDeliveryError(RuntimeError):
    pass


def send_sms_message(to_phone: str, body: str) -> None:
    """Send an SMS via Twilio. Raises SmsDeliveryError if not configured or delivery fails."""
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN or not settings.TWILIO_FROM_PHONE:
        raise SmsDeliveryError("SMS (Twilio) no configurado")

    try:
        from twilio.rest import Client  # type: ignore[import-untyped]
    except ImportError as exc:
        raise SmsDeliveryError("Librería twilio no instalada") from exc

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=body,
            from_=settings.TWILIO_FROM_PHONE,
            to=to_phone,
        )
    except Exception as exc:  # pragma: no cover - depends on external Twilio
        raise SmsDeliveryError(str(exc)) from exc


def send_mfa_sms_code(to_phone: str, code: str, expires_minutes: int) -> None:
    body = (
        f"SOPHIE: Tu código de verificación es {code}. "
        f"Expira en {expires_minutes} minutos. "
        "Si no solicitaste esto, ignora este mensaje."
    )
    send_sms_message(to_phone=to_phone, body=body)
