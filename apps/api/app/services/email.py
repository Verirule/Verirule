from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.settings import get_settings


class InviteEmailNotConfiguredError(RuntimeError):
    pass


class InviteEmailSendError(RuntimeError):
    pass


def send_org_invite_email(*, recipient_email: str, invite_link: str, org_id: str, role: str) -> None:
    settings = get_settings()

    host = (settings.SMTP_HOST or "").strip()
    from_email = (settings.EMAIL_FROM or "").strip()
    if not host or not from_email:
        raise InviteEmailNotConfiguredError("SMTP transport is not configured.")

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = recipient_email
    message["Subject"] = "You were invited to Verirule"
    message.set_content(
        "\n".join(
            [
                "You have been invited to join a Verirule workspace.",
                f"Organization: {org_id}",
                f"Role: {role}",
                "",
                f"Accept invite: {invite_link}",
            ]
        )
    )

    try:
        if settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(host=host, port=settings.SMTP_PORT, timeout=10) as server:
                _smtp_login_if_needed(server)
                server.send_message(message)
            return

        with smtplib.SMTP(host=host, port=settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            _smtp_login_if_needed(server)
            server.send_message(message)
    except OSError as exc:
        raise InviteEmailSendError("Failed to send invite email.") from exc


def _smtp_login_if_needed(server: smtplib.SMTP) -> None:
    settings = get_settings()
    username = (settings.SMTP_USERNAME or "").strip()
    password = settings.SMTP_PASSWORD
    if username and password:
        server.login(username, password)
