from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select, update

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
from app.db.models import (
    AuthIdentity,
    Goal,
    RoadmapGenerationAttempt,
    RoadmapStepProgress,
    RoadmapStepResourceFeedback,
    RoadmapStepResourceRefreshAttempt,
    RoadmapStepWork,
    User,
    UserSession,
)
from app.services.identity import (
    IdentityProvider,
    IdentityProviderNotConfigured,
    IdentityTokenError,
    IdentityVerifier,
    VerifiedIdentity,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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
    settings = get_settings()
    providers = sorted(identity.provider for identity in user.identities)
    email = next((identity.email for identity in user.identities if identity.email), "")
    return AccountRead(
        user_id=user.id,
        status="saved" if providers else "guest",
        providers=providers,
        email=email,
        provider_config=AuthProviderConfigRead(
            apple=bool(settings.allowed_apple_client_ids),
            google=bool(settings.google_client_ids),
            google_web_client_id=settings.google_web_client_id,
            google_ios_client_id=settings.google_ios_client_id,
            google_android_client_id=settings.google_android_client_id,
        ),
    )


def update_identity(identity: AuthIdentity, verified: VerifiedIdentity) -> None:
    if verified.email:
        identity.email = verified.email
    if verified.display_name:
        identity.display_name = verified.display_name
    identity.last_sign_in_at = datetime.now(UTC)


def merge_guest_data(db: DbSession, source_user: User, target_user: User) -> None:
    owned_models = (
        Goal,
        RoadmapGenerationAttempt,
        RoadmapStepProgress,
        RoadmapStepWork,
        RoadmapStepResourceRefreshAttempt,
        RoadmapStepResourceFeedback,
    )
    for model in owned_models:
        db.execute(
            update(model).where(model.user_id == source_user.id).values(user_id=target_user.id)
        )
    db.flush()
    db.delete(source_user)


@router.post(
    "/anonymous",
    response_model=AnonymousSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_anonymous_session(db: DbSession) -> AnonymousSessionRead:
    user = User()
    db.add(user)
    db.flush()
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
) -> AnonymousSessionRead:
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

    target_user = user
    current_session.revoked_at = datetime.now(UTC)
    if existing_identity is not None and existing_identity.user_id != user.id:
        if user.identities:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sign out before switching to a different saved account",
            )
        target_user = db.get(User, existing_identity.user_id)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The saved account could not be opened",
            )
        update_identity(existing_identity, verified)
        merge_guest_data(db, user, target_user)
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

    replacement = issue_session(db, target_user)
    db.commit()
    return replacement


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_session: CurrentSession, db: DbSession) -> Response:
    current_session.revoked_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user: CurrentUser, db: DbSession) -> Response:
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
