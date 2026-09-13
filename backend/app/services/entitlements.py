from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Goal, RoadmapStep, RoadmapVersion, User

FREE_GOAL_LIMIT = 2


def is_premium(user: User) -> bool:
    return user.subscription_tier == "premium"


def goal_count(db: Session, user: User) -> int:
    return int(
        db.scalar(
            select(func.count(Goal.id)).where(Goal.user_id == user.id)
        )
        or 0
    )


def can_create_goal(db: Session, user: User) -> bool:
    return is_premium(user) or goal_count(db, user) < FREE_GOAL_LIMIT


def unlocked_milestone_limit(user: User, roadmap: RoadmapVersion) -> int | None:
    """Return the free milestone boundary, or None when the whole roadmap is available.

    A zero value grandfathered pre-entitlement roadmaps so existing learner progress is not
    unexpectedly removed when the feature ships.
    """
    if is_premium(user) or roadmap.free_access_milestones <= 0:
        return None
    return roadmap.free_access_milestones


def can_access_step(user: User, roadmap: RoadmapVersion, step: RoadmapStep) -> bool:
    limit = unlocked_milestone_limit(user, roadmap)
    return limit is None or step.milestone.position <= limit
