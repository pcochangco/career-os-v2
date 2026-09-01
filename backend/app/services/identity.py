from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends

from app.core.config import Settings, get_settings

IdentityProvider = Literal["apple", "google"]


class IdentityTokenError(ValueError):
    pass


class IdentityProviderNotConfigured(IdentityTokenError):
    pass


@dataclass(frozen=True)
class VerifiedIdentity:
    provider: IdentityProvider
    subject: str
    email: str = ""
    display_name: str = ""


class IdentityTokenVerifier:
    JWKS_URLS = {
        "apple": "https://appleid.apple.com/auth/keys",
        "google": "https://www.googleapis.com/oauth2/v3/certs",
    }
    ISSUERS = {
        "apple": {"https://appleid.apple.com"},
        "google": {"accounts.google.com", "https://accounts.google.com"},
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def verify(self, provider: IdentityProvider, identity_token: str) -> VerifiedIdentity:
        audiences = self._audiences(provider)
        if not audiences:
            raise IdentityProviderNotConfigured(f"{provider.title()} sign-in is not configured")

        try:
            import jwt
            from jwt import PyJWKClient

            signing_key = PyJWKClient(self.JWKS_URLS[provider]).get_signing_key_from_jwt(
                identity_token
            )
            claims = jwt.decode(
                identity_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=audiences,
                options={"require": ["aud", "exp", "iss", "sub"]},
            )
        except Exception as error:
            raise IdentityTokenError("The identity token could not be verified") from error

        if claims.get("iss") not in self.ISSUERS[provider]:
            raise IdentityTokenError("The identity token issuer is invalid")

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject or len(subject) > 255:
            raise IdentityTokenError("The identity token subject is invalid")

        email = claims.get("email")
        email_verified = claims.get("email_verified")
        verified_email = (
            email
            if isinstance(email, str)
            and len(email) <= 320
            and email_verified in {True, "true", "True", "1"}
            else ""
        )
        display_name = claims.get("name")
        if not isinstance(display_name, str) or len(display_name) > 120:
            display_name = ""

        return VerifiedIdentity(
            provider=provider,
            subject=subject,
            email=verified_email,
            display_name=display_name,
        )

    def _audiences(self, provider: IdentityProvider) -> list[str]:
        if provider == "google":
            return self.settings.google_client_ids
        return self.settings.allowed_apple_client_ids


def get_identity_token_verifier() -> IdentityTokenVerifier:
    return IdentityTokenVerifier(get_settings())


IdentityVerifier = Annotated[IdentityTokenVerifier, Depends(get_identity_token_verifier)]
