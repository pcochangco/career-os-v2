"""Send the one-time sign-in code. "log" prints it (local only); "resend" emails it."""

import logging

import httpx

from app.core.config import Settings

logger = logging.getLogger("careeros.email")


class EmailDeliveryError(Exception):
    pass


def send_sign_in_code(settings: Settings, email: str, code: str) -> None:
    if settings.email_sender == "log":
        # Settings.email_code_login_ready keeps this sender out of production.
        logger.warning("Sign-in code for %s: %s (log sender, local only)", email, code)
        return
    assert settings.resend_api_key is not None
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key.get_secret_value()}"},
            json={
                "from": settings.email_from,
                "to": [email],
                "subject": f"{code} is your CareerOS sign-in code",
                "text": (
                    f"Your CareerOS sign-in code is {code}\n\n"
                    "It expires in 10 minutes and works once. If you didn't ask for it, "
                    "you can ignore this email."
                ),
            },
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        # Never log the code or the API key; the status is enough to diagnose.
        logger.error("Sign-in email failed: %s", type(error).__name__)
        raise EmailDeliveryError from error
