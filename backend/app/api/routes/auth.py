from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.api.dependencies import (
    CurrentSession,
    CurrentUser,
    DbSession,
    hash_session_token,
)
from app.api.schemas import (
    AccountRead,
    AnonymousSessionRead,
    AuthProviderConfigRead,
    IdentityLinkWrite,
)
from app.core.config import get_settings
from app.core.rate_limit import SlidingWindowRateLimiter, get_auth_rate_limiter
from app.db.models import AuthIdentity, User, UserSession
from app.services.identity import (
    IdentityProvider,
    IdentityProviderNotConfigured,
    IdentityTokenError,
    IdentityVerifier,
    VerifiedIdentity,
)

router = APIRouter(prefix="/auth", tags=["auth"])
AuthRateLimiter = Annotated[SlidingWindowRateLimiter, Depends(get_auth_rate_limiter)]


def enforce_rate_limit(
    limiter: SlidingWindowRateLimiter,
    *,
    action: str,
    source: str,
    limit: int,
) -> None:
    source_hash = sha256(source.encode("utf-8")).hexdigest()
    decision = limiter.check(
        f"{action}:{source_hash}",
        limit=limit,
        window_seconds=15 * 60,
    )
    if decision.allowed:
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many account requests. Please wait and try again.",
        headers={"Retry-After": str(decision.retry_after_seconds)},
    )


def issue_session(db: DbSession, user: User) -> AnonymousSessionRead:
    token = token_urlsafe(32)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(UTC) + timedelta(days=180),
        )
    )
    return AnonymousSessionRead(access_token=token, user_id=user.id)


def account_response(user: User) -> AccountRead:
    providers = sorted(identity.provider for identity in user.identities)
    email = next((identity.email for identity in user.identities if identity.email), "")
    return AccountRead(
        user_id=user.id,
        status="saved" if providers else "guest",
        providers=providers,
        email=email,
        provider_config=provider_config_response(),
    )


def provider_config_response() -> AuthProviderConfigRead:
    settings = get_settings()
    return AuthProviderConfigRead(
        apple=bool(settings.allowed_apple_client_ids),
        google=bool(settings.google_client_ids),
        google_web_client_id=settings.google_web_client_id,
        google_ios_client_id=settings.google_ios_client_id,
        google_android_client_id=settings.google_android_client_id,
    )


def update_identity(identity: AuthIdentity, verified: VerifiedIdentity) -> None:
    if verified.email:
        identity.email = verified.email
    if verified.display_name:
        identity.display_name = verified.display_name
    identity.last_sign_in_at = datetime.now(UTC)


@router.post(
    "/anonymous",
    response_model=AnonymousSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_anonymous_session(
    request: Request,
    db: DbSession,
    limiter: AuthRateLimiter,
) -> AnonymousSessionRead:
    settings = get_settings()
    if not settings.allow_guest_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guest access is not available",
        )
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "")[:160]
    enforce_rate_limit(
        limiter,
        action="anonymous",
        source=f"{client_host}:{user_agent}",
        limit=settings.auth_anonymous_limit_per_15_minutes,
    )
    user = User()
    db.add(user)
    db.flush()
    session = issue_session(db, user)
    db.commit()
    return session


@router.get("/config", response_model=AuthProviderConfigRead)
def read_provider_config() -> AuthProviderConfigRead:
    return provider_config_response()


@router.post("/sign-in/{provider}", response_model=AnonymousSessionRead)
def sign_in(
    provider: IdentityProvider,
    payload: IdentityLinkWrite,
    request: Request,
    db: DbSession,
    verifier: IdentityVerifier,
    limiter: AuthRateLimiter,
) -> AnonymousSessionRead:
    settings = get_settings()
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "")[:160]
    enforce_rate_limit(
        limiter,
        action=f"sign-in:{provider}",
        source=f"{client_host}:{user_agent}",
        limit=settings.auth_identity_limit_per_15_minutes,
    )
    try:
        verified = verifier.verify(provider, payload.identity_token)
    except IdentityProviderNotConfigured as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except IdentityTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The sign-in response could not be verified",
        ) from error

    identity = db.scalar(
        select(AuthIdentity).where(
            AuthIdentity.provider == provider,
            AuthIdentity.subject == verified.subject,
        )
    )
    if identity is None:
        user = User()
        db.add(user)
        db.flush()
        identity = AuthIdentity(
            user_id=user.id,
            provider=provider,
            subject=verified.subject,
            email=verified.email,
            display_name=verified.display_name,
        )
        db.add(identity)
    else:
        user = db.get(User, identity.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The saved account could not be opened",
            )
        update_identity(identity, verified)

    session = issue_session(db, user)
    db.commit()
    return session


@router.get("/account", response_model=AccountRead)
def read_account(user: CurrentUser) -> AccountRead:
    return account_response(user)


@router.post("/link/{provider}", response_model=AnonymousSessionRead)
def link_identity(
    provider: IdentityProvider,
    payload: IdentityLinkWrite,
    user: CurrentUser,
    current_session: CurrentSession,
    db: DbSession,
    verifier: IdentityVerifier,
    limiter: AuthRateLimiter,
) -> AnonymousSessionRead:
    settings = get_settings()
    if not user.identities:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sign in before linking another provider",
        )
    enforce_rate_limit(
        limiter,
        action=f"link:{provider}",
        source=str(user.id),
        limit=settings.auth_identity_limit_per_15_minutes,
    )
    try:
        verified = verifier.verify(provider, payload.identity_token)
    except IdentityProviderNotConfigured as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except IdentityTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The sign-in response could not be verified",
        ) from error

    existing_identity = db.scalar(
        select(AuthIdentity).where(
            AuthIdentity.provider == provider,
            AuthIdentity.subject == verified.subject,
        )
    )
    current_provider_identity = db.scalar(
        select(AuthIdentity).where(
            AuthIdentity.user_id == user.id,
            AuthIdentity.provider == provider,
        )
    )

    if current_provider_identity is not None and (
        existing_identity is None or current_provider_identity.id != existing_identity.id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A different {provider.title()} account is already linked",
        )

    current_session.revoked_at = datetime.now(UTC)
    if existing_identity is not None and existing_identity.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"That {provider.title()} account belongs to another CareerOS account",
        )
    elif existing_identity is not None:
        update_identity(existing_identity, verified)
    else:
        db.add(
            AuthIdentity(
                user_id=user.id,
                provider=provider,
                subject=verified.subject,
                email=verified.email,
                display_name=verified.display_name,
            )
        )

    replacement = issue_session(db, user)
    db.commit()
    return replacement


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_session: CurrentSession, db: DbSession) -> Response:
    current_session.revoked_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    user: CurrentUser,
    db: DbSession,
    limiter: AuthRateLimiter,
) -> Response:
    settings = get_settings()
    enforce_rate_limit(
        limiter,
        action="delete",
        source=str(user.id),
        limit=settings.auth_deletion_limit_per_15_minutes,
    )
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
