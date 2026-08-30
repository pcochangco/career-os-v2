from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.resources.dependencies import get_resource_resolver
from app.resources.providers import CuratedVideoProvider, WikipediaResourceProvider
from app.resources.schema import ResourceCandidate
from app.resources.service import ResourceResolver
from tests.test_progress import auth, create_accepted_roadmap, create_session, steps_in


class RecordingProvider:
    def __init__(self, candidates: list[ResourceCandidate]) -> None:
        self.candidates = candidates
        self.calls = 0

    def search(self, query: str, limit: int) -> list[ResourceCandidate]:
        del query, limit
        self.calls += 1
        return self.candidates


class StubResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def candidate(
    *,
    url: str = "https://en.wikipedia.org/wiki/Intelligent_agent",
    title: str = "Intelligent agent",
    resource_type: str = "article",
) -> ResourceCandidate:
    return ResourceCandidate(
        provider="test",
        resource_type=resource_type,
        title=title,
        url=url,
        source_name="Wikipedia",
        description="A verified overview.",
        why_relevant="Useful background for the current step.",
        thumbnail_url="",
        verified_at=datetime.now(UTC),
    )


def test_current_step_resources_are_verified_persisted_and_cached(client: TestClient) -> None:
    token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, token)
    current_step = steps_in(roadmap)[0]
    provider = RecordingProvider(
        [
            candidate(),
            candidate(
                url="https://www.youtube.com/watch?v=Unzc731iCUY",
                title="How to Speak",
                resource_type="video",
            ),
        ]
    )
    app.dependency_overrides[get_resource_resolver] = lambda: ResourceResolver([provider])

    first = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )
    second = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )

    assert first.status_code == 200
    assert first.json()["available"] is True
    assert first.json()["cached"] is False
    assert [resource["resource_type"] for resource in first.json()["resources"]] == [
        "article",
        "video",
    ]
    assert all(resource["verified_at"] for resource in first.json()["resources"])
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert [resource["id"] for resource in second.json()["resources"]] == [
        resource["id"] for resource in first.json()["resources"]
    ]
    assert [resource["url"] for resource in second.json()["resources"]] == [
        resource["url"] for resource in first.json()["resources"]
    ]
    assert provider.calls == 1


def test_unsafe_or_incomplete_candidates_are_not_stored(client: TestClient) -> None:
    token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, token)
    current_step = steps_in(roadmap)[0]
    provider = RecordingProvider(
        [
            candidate(url="http://127.0.0.1/internal"),
            candidate(url="https://malicious.example/resource"),
            candidate(title=""),
        ]
    )
    app.dependency_overrides[get_resource_resolver] = lambda: ResourceResolver([provider])

    response = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )

    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["resources"] == []
    assert response.json()["message"]


def test_resources_cannot_be_loaded_early_or_by_another_user(client: TestClient) -> None:
    owner_token = create_session(client)
    other_token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, owner_token)
    blocked_step = steps_in(roadmap)[1]
    provider = RecordingProvider([candidate()])
    app.dependency_overrides[get_resource_resolver] = lambda: ResourceResolver([provider])

    early = client.post(
        f"/api/v1/roadmap-steps/{blocked_step['id']}/resources/resolve",
        headers=auth(owner_token),
    )
    not_owned = client.post(
        f"/api/v1/roadmap-steps/{blocked_step['id']}/resources/resolve",
        headers=auth(other_token),
    )

    assert early.status_code == 409
    assert not_owned.status_code == 404
    assert provider.calls == 0


def test_wikipedia_provider_uses_topic_query_and_verified_api_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request: dict = {}

    def fake_get(url: str, **kwargs: object) -> StubResponse:
        request.update({"url": url, **kwargs})
        return StubResponse(
            {
                "query": {
                    "pages": [
                        {
                            "title": "Intelligent agent",
                            "fullurl": "https://en.wikipedia.org/wiki/Intelligent_agent",
                            "extract": "An intelligent agent perceives and acts.",
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr("app.resources.providers.httpx.get", fake_get)
    resources = WikipediaResourceProvider(2).search(
        "AI agent engineering competency framework beginner guide",
        2,
    )

    assert request["url"] == WikipediaResourceProvider.endpoint
    assert request["params"]["gsrsearch"] == "AI agent engineering"
    assert resources[0].title == "Intelligent agent"
    assert resources[0].resource_type == "article"
    assert resources[0].verified_at is not None


def test_curated_video_provider_verifies_youtube_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(url: str, **kwargs: object) -> StubResponse:
        assert url == "https://www.youtube.com/oembed"
        assert kwargs["params"]["format"] == "json"
        return StubResponse(
            {
                "title": "How to practice effectively",
                "author_name": "TED-Ed",
                "thumbnail_url": "https://i.ytimg.com/vi/example/hqdefault.jpg",
            }
        )

    monkeypatch.setattr("app.resources.providers.httpx.get", fake_get)
    resources = CuratedVideoProvider(2).search("complete practical tutorial", 2)

    assert len(resources) == 1
    assert resources[0].source_name == "TED-Ed"
    assert resources[0].resource_type == "video"
