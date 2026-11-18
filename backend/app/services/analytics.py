"""Privacy-safe product funnel events, stored in CareerOS's own database.

Events are recorded on the server at the moment the action happens, inside the same
transaction, so there is no client tracking, no cookies and no third party. Only the event
names and property values listed here are accepted; free text is never stored.

Funnel: signup_completed -> goal_created -> discovery_completed -> roadmap_generated ->
roadmap_accepted -> step_completed (first_ever) -> active_day (a later day = returned).
"""

from datetime import UTC, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ProductEvent, User

ALLOWED_PROPERTIES: dict[str, dict[str, frozenset | type]] = {
    "signup_completed": {"method": frozenset({"apple", "google", "email"})},
    "goal_created": {"first": bool},
    "goal_limit_reached": {},
    "discovery_completed": {"all_skipped": bool},
    "roadmap_generated": {
        "source": frozenset({"succeeded", "fallback", "quota_fallback", "preview"})
    },
    "roadmap_accepted": {},
    "step_completed": {"first_ever": bool},
    "practice_logged": {},
    "active_day": {},
}


def record_event(db: Session, user: User, event: str, **properties: str | bool) -> None:
    """Add an event to the current transaction; the caller's commit persists it."""
    allowed = ALLOWED_PROPERTIES.get(event)
    if allowed is None:
        raise ValueError(f"Unknown product event: {event}")
    clean: dict[str, str | bool] = {}
    for key, value in properties.items():
        rule = allowed.get(key)
        is_allowed_flag = rule is bool and isinstance(value, bool)
        is_allowed_choice = isinstance(rule, frozenset) and value in rule
        if is_allowed_flag or is_allowed_choice:
            clean[key] = value
        # Anything else is dropped rather than stored.
    db.add(ProductEvent(user_id=user.id, event=event, properties=clean))


def record_active_day(db: Session, user: User) -> None:
    """Record at most one active_day per user per UTC day (used for day-2 return)."""
    start = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
    seen_today = db.scalar(
        select(ProductEvent.id)
        .where(
            ProductEvent.user_id == user.id,
            ProductEvent.event == "active_day",
            ProductEvent.occurred_at >= start,
        )
        .limit(1)
    )
    if seen_today is None:
        record_event(db, user, "active_day")
        db.commit()
