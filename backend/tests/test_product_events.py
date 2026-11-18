"""Funnel events are recorded server-side, contain no free text, and leave with the account."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import ProductEvent, User
from app.db.session import get_db
from app.main import app
from app.services.analytics import record_event
from app.services.funnel import funnel_report

DISCOVERY = {
    "desired_outcome": "Hold a 10 minute conversation in Spanish",
    "current_level": "Beginner with some vocabulary",
    "existing_experience": "Duolingo for three months",
    "relevant_constraints": "Thirty minutes on weekdays",
    "proof_of_completion": "A recorded conversation with a tutor",
}


def db_session():
    return next(app.dependency_overrides[get_db]())


def events(event: str | None = None) -> list[ProductEvent]:
    query = select(ProductEvent)
    if event:
        query = query.where(ProductEvent.event == event)
    return list(db_session().scalars(query).all())


def test_journey_records_each_funnel_step(client: TestClient) -> None:
    headers = {
        "Authorization": "Bearer " + client.post("/api/v1/auth/anonymous").json()["access_token"]
    }
    goal = client.post(
        "/api/v1/goals", headers=headers, json={"title": "Learn conversational Spanish"}
    ).json()
    client.put(f"/api/v1/goals/{goal['id']}/discovery", headers=headers, json=DISCOVERY)
    roadmap = client.post(f"/api/v1/goals/{goal['id']}/roadmaps", headers=headers).json()
    roadmap = client.post(f"/api/v1/roadmaps/{roadmap['id']}/accept", headers=headers).json()
    client.put(
        f"/api/v1/roadmap-steps/{roadmap['current_step_id']}/progress",
        headers=headers,
        json={"completed": True, "completion_confirmed": True},
    )
    client.put(f"/api/v1/roadmaps/{roadmap['id']}/practice/today", headers=headers)
    client.get("/api/v1/auth/account", headers=headers)
    client.get("/api/v1/auth/account", headers=headers)

    names = [event.event for event in events()]
    assert names.count("goal_created") == 1
    assert "discovery_completed" in names
    assert "roadmap_generated" in names
    assert "roadmap_accepted" in names
    assert "practice_logged" in names
    assert names.count("active_day") == 1  # once per day, however often the app opens
    [created] = events("goal_created")
    assert created.properties == {"first": True}
    [completed] = events("step_completed")
    assert completed.properties == {"first_ever": True}
    [generated] = events("roadmap_generated")
    assert generated.properties["source"] in {"succeeded", "fallback", "quota_fallback", "preview"}


def test_events_never_store_free_text(client: TestClient) -> None:
    headers = {
        "Authorization": "Bearer " + client.post("/api/v1/auth/anonymous").json()["access_token"]
    }
    client.post("/api/v1/goals", headers=headers, json={"title": "A very private goal title"})

    for event in events():
        assert "private" not in str(event.properties)


def test_unknown_events_and_properties_are_rejected_or_dropped(client: TestClient) -> None:
    db = db_session()
    user = User()
    db.add(user)
    db.flush()

    with pytest.raises(ValueError):
        record_event(db, user, "page_viewed")

    record_event(db, user, "signup_completed", method="email", email="someone@example.com")
    record_event(db, user, "roadmap_generated", source="not-a-source")
    db.commit()

    by_name = {event.event: event.properties for event in events()}
    assert by_name["signup_completed"] == {"method": "email"}
    assert by_name["roadmap_generated"] == {}


def test_events_are_deleted_with_the_account(client: TestClient) -> None:
    headers = {
        "Authorization": "Bearer " + client.post("/api/v1/auth/anonymous").json()["access_token"]
    }
    client.post("/api/v1/goals", headers=headers, json={"title": "Learn conversational Spanish"})
    assert events()

    assert client.delete("/api/v1/auth/account", headers=headers).status_code == 204

    assert events() == []


def test_funnel_report_counts_people_per_step(client: TestClient) -> None:
    db = db_session()
    now = datetime.now(UTC)
    people = []
    for _ in range(3):
        user = User()
        db.add(user)
        db.flush()
        people.append(user)
        db.add(
            ProductEvent(
                user_id=user.id,
                event="signup_completed",
                properties={"method": "email"},
                occurred_at=now - timedelta(days=2),
            )
        )
    first, second, _ = people
    for user in (first, second):
        db.add(ProductEvent(user_id=user.id, event="goal_created", properties={"first": True}))
    db.add(ProductEvent(user_id=first.id, event="roadmap_accepted", properties={}))
    db.add(ProductEvent(user_id=first.id, event="active_day", properties={}, occurred_at=now))
    db.commit()

    report = dict(funnel_report(db, days=30))

    assert report["Signed up"] == 3
    assert report["Created a first goal"] == 2
    assert report["Accepted a roadmap"] == 1
    assert report["Came back on a later day"] == 1
