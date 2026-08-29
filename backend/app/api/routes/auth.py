from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from fastapi import APIRouter, status

from app.api.dependencies import DbSession, hash_session_token
from app.api.schemas import AnonymousSessionRead
from app.db.models import User, UserSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/anonymous",
    response_model=AnonymousSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_anonymous_session(db: DbSession) -> AnonymousSessionRead:
    token = token_urlsafe(32)
    user = User()
    db.add(user)
    db.flush()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(UTC) + timedelta(days=180),
        )
    )
    db.commit()
    return AnonymousSessionRead(access_token=token, user_id=user.id)
