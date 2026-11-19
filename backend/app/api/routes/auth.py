from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import compare_digest, randbelow, token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

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
    EmailCodeRequestWrite,
    EmailCodeVerifyWrite,
    EmailTestSignInWrite,
    IdentityLinkWrite,
)
from app.core.config import get_settings
from app.core.rate_limit import SlidingWindowRateLimiter, get_auth_rate_limiter
from app.db.models import AuthIdentity, EmailSignInCode, User, UserSession
from app.services.analytics import record_active_day, record_event
from app.services.data_export import build_account_export
from app.services.email import EmailDeliveryError, send_sign_in_code
from app.services.entitlements import FREE_GOAL_LIMIT, is_premium
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
        plan="premium" if is_premium(user) else "free",
        goal_limit=None if is_premium(user) else FREE_GOAL_LIMIT,
    )


def provider_config_response() -> AuthProviderConfigRead:
    settings = get_settings()
    return AuthProviderConfigRead(
        apple=bool(settings.allowed_apple_client_ids),
        google=bool(settings.google_client_ids),
        email_test=settings.email_test_login_enabled,
        email_code=settings.email_code_login_ready,
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


@router.post("/email-test-sign-in", response_model=AnonymousSessionRead)
def sign_in_with_email_test_access(
    payload: EmailTestSignInWrite,
    request: Request,
    db: DbSession,
    limiter: AuthRateLimiter,
) -> AnonymousSessionRead:
    """Temporary, allowlisted sign-in while production email delivery is unavailable.

    This is deliberately not a general email/password provider: only operator-approved
    emails plus an environment-held access code can use it. Real email verification
    will replace this once a sending domain is configured.
    """
    settings = get_settings()
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "")[:160]
    enforce_rate_limit(
        limiter,
        action="email-test-sign-in",
        source=f"{client_host}:{user_agent}",
        limit=settings.auth_identity_limit_per_15_minutes,
    )
    email = payload.email.casefold()
    configured_code = (
        settings.email_test_access_code.get_secret_value()
        if settings.email_test_access_code is not None
        else ""
    )
    if (
        not settings.email_test_login_enabled
        or email not in settings.email_test_login_email_set
        or not compare_digest(payload.access_code, configured_code)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email sign-in could not be verified.",
        )

    session = session_for_verified_email(db, email)
    db.commit()
    return session


def session_for_verified_email(db: DbSession, email: str) -> AnonymousSessionRead:
    """Sign in the account that owns this (already verified) email, creating it if new."""
    identity = db.scalar(
        select(AuthIdentity).where(func.lower(AuthIdentity.email) == email)
    )
    if identity is None:
        user = User()
        db.add(user)
        db.flush()
        record_event(db, user, "signup_completed", method="email")
        db.add(
            AuthIdentity(
                user_id=user.id,
                provider="email",
                subject=email,
                email=email,
                display_name="",
            )
        )
    else:
        user = db.get(User, identity.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The saved account could not be opened.",
            )
        identity.last_sign_in_at = datetime.now(UTC)
    return issue_session(db, user)


EMAIL_CODE_TTL = timedelta(minutes=10)
EMAIL_CODE_MAX_ATTEMPTS = 5
EMAIL_CODE_REQUESTS_PER_EMAIL = 5
EMAIL_CODE_FAILED = "That code didn't work. Check it, or request a new one."


def hash_email_code(email: str, code: str) -> str:
    return sha256(f"{email}:{code}".encode()).hexdigest()


def require_email_code_login() -> None:
    if not get_settings().email_code_login_ready:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email sign-in isn't available yet.",
        )


def client_source(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{request.headers.get('User-Agent', '')[:160]}"


@router.post("/email-code/request", status_code=status.HTTP_202_ACCEPTED)
def request_email_code(
    payload: EmailCodeRequestWrite,
    request: Request,
    db: DbSession,
    limiter: AuthRateLimiter,
) -> Response:
    """Email a one-time code. Same response whether or not an account exists."""
    require_email_code_login()
    settings = get_settings()
    enforce_rate_limit(
        limiter,
        action="email-code-request",
        source=client_source(request),
        limit=settings.auth_identity_limit_per_15_minutes,
    )
    enforce_rate_limit(
        limiter,
        action="email-code-request-email",
        source=payload.email,
        limit=EMAIL_CODE_REQUESTS_PER_EMAIL,
    )
    now = datetime.now(UTC)
    for previous in db.scalars(
        select(EmailSignInCode).where(
            EmailSignInCode.email == payload.email, EmailSignInCode.consumed_at.is_(None)
        )
    ):
        previous.consumed_at = now  # only the newest code works
    code = f"{randbelow(1_000_000):06d}"
    db.add(
        EmailSignInCode(
            email=payload.email,
            code_hash=hash_email_code(payload.email, code),
            expires_at=now + EMAIL_CODE_TTL,
        )
    )
    db.commit()
    try:
        send_sign_in_code(settings, payload.email, code)
    except EmailDeliveryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="We couldn't send the email. Try again in a minute.",
        ) from error
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/email-code/verify", response_model=AnonymousSessionRead)
def verify_email_code(
    payload: EmailCodeVerifyWrite,
    request: Request,
    db: DbSession,
    limiter: AuthRateLimiter,
) -> AnonymousSessionRead:
    require_email_code_login()
    enforce_rate_limit(
        limiter,
        action="email-code-verify",
        source=client_source(request),
        limit=get_settings().auth_identity_limit_per_15_minutes,
    )
    row = db.scalar(
        select(EmailSignInCode)
        .where(EmailSignInCode.email == payload.email, EmailSignInCode.consumed_at.is_(None))
        .order_by(EmailSignInCode.created_at.desc())
        .limit(1)
    )
    now = datetime.now(UTC)
    if row is None or row.attempts >= EMAIL_CODE_MAX_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=EMAIL_CODE_FAILED)
    # SQLite returns naive datetimes; Postgres returns aware ones.
    expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
    if expires_at <= now or not compare_digest(
        row.code_hash, hash_email_code(payload.email, payload.code)
    ):
        row.attempts += 1
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=EMAIL_CODE_FAILED)
    row.consumed_at = now
    session = session_for_verified_email(db, payload.email)
    db.commit()
    return session


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
        record_event(db, user, "signup_completed", method=provider)
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
def read_account(user: CurrentUser, db: DbSession) -> AccountRead:
    record_active_day(db, user)
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


@router.get("/account/export")
def export_account(user: CurrentUser, limiter: AuthRateLimiter) -> JSONResponse:
    """Download everything this person has created, as JSON. No AI calls."""
    enforce_rate_limit(
        limiter,
        action="export",
        source=str(user.id),
        limit=get_settings().auth_deletion_limit_per_15_minutes,
    )
    filename = f"careeros-export-{datetime.now(UTC):%Y-%m-%d}.json"
    return JSONResponse(
        build_account_export(user),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


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
