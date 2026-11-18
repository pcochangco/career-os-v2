"""Aggregate funnel counts from product events (distinct people per step)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ProductEvent

FUNNEL_STEPS = [
    ("Signed up", "signup_completed", None),
    ("Created a first goal", "goal_created", ("first", True)),
    ("Finished discovery", "discovery_completed", None),
    ("Got a roadmap", "roadmap_generated", None),
    ("Accepted a roadmap", "roadmap_accepted", None),
    ("Completed a first step", "step_completed", ("first_ever", True)),
]


def _people(db: Session, event: str, since: datetime, match: tuple | None) -> set:
    rows = db.execute(
        select(ProductEvent.user_id, ProductEvent.properties).where(
            ProductEvent.event == event, ProductEvent.occurred_at >= since
        )
    ).all()
    return {
        user_id
        for user_id, properties in rows
        if match is None or (properties or {}).get(match[0]) == match[1]
    }


def funnel_report(db: Session, *, days: int = 30) -> list[tuple[str, int]]:
    """People who reached each step, among those who signed up in the window."""
    since = datetime.now(UTC) - timedelta(days=days)
    cohort = _people(db, "signup_completed", since, None)
    report = []
    for label, event, match in FUNNEL_STEPS:
        if event == "signup_completed":
            reached = cohort
        else:
            reached = cohort & _people(db, event, since, match)
        report.append((label, len(reached)))

    # Returned on a later day: an active_day on any UTC day after the signup day.
    signup_day = dict(
        db.execute(
            select(ProductEvent.user_id, func.min(ProductEvent.occurred_at))
            .where(ProductEvent.event == "signup_completed", ProductEvent.occurred_at >= since)
            .group_by(ProductEvent.user_id)
        ).all()
    )
    returned = set()
    for user_id, occurred_at in db.execute(
        select(ProductEvent.user_id, ProductEvent.occurred_at).where(
            ProductEvent.event == "active_day", ProductEvent.occurred_at >= since
        )
    ).all():
        first = signup_day.get(user_id)
        if first is not None and occurred_at.date() > first.date():
            returned.add(user_id)
    report.append(("Came back on a later day", len(cohort & returned)))
    return report
