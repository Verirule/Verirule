from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger("notifications.emailer")


class EmailNotConfiguredError(RuntimeError):
    pass


class EmailSendError(RuntimeError):
    pass


def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    text: str,
    request_id: str | None = None,
) -> None:
    settings = get_settings()
    host = (settings.SMTP_HOST or "").strip()
    from_email = (settings.EMAIL_FROM or "").strip()
    if not host or not from_email:
        raise EmailNotConfiguredError("SMTP transport is not configured.")

    recipient_domain = _recipient_domain(to)

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    try:
        if settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(host=host, port=settings.SMTP_PORT, timeout=10) as server:
                _smtp_login_if_needed(server)
                server.send_message(message)
        else:
            with smtplib.SMTP(host=host, port=settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                _smtp_login_if_needed(server)
                server.send_message(message)
    except OSError as exc:
        logger.warning(
            "notifications.email_send_failed",
            extra={
                "component": "worker",
                "request_id": request_id,
                "recipient_domain": recipient_domain,
            },
        )
        raise EmailSendError("Failed to send notification email.") from exc

    logger.info(
        "notifications.email_sent",
        extra={
            "component": "worker",
            "request_id": request_id,
            "recipient_domain": recipient_domain,
        },
    )


def _recipient_domain(recipient: str) -> str:
    value = recipient.strip().lower()
    if "@" not in value:
        return "unknown"
    return value.rsplit("@", maxsplit=1)[-1] or "unknown"


def _smtp_login_if_needed(server: smtplib.SMTP) -> None:
    settings = get_settings()
    username = (settings.SMTP_USERNAME or "").strip()
    password = settings.SMTP_PASSWORD
    if username and password:
        server.login(username, password)

