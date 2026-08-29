from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import hash_session_token
from app.api.schemas import AnonymousSessionRead
from app.db.models import User, UserSession
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/anonymous",
    response_model=AnonymousSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_anonymous_session(db: Session = Depends(get_db)) -> AnonymousSessionRead:
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
