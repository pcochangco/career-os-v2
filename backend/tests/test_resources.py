from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.routes import resources as resource_routes
from app.core.config import Settings
from app.main import app
from app.resources.dependencies import get_resource_resolver
from app.resources.providers import BraveSearchResourceProvider, YouTubeResourceProvider
from app.resources.schema import ResourceCandidate
from app.resources.service import ResourceResolver
from tests.test_progress import auth, create_accepted_roadmap, create_session, steps_in


class RecordingProvider:
    def __init__(self, candidates: list[ResourceCandidate], name: str = "test") -> None:
        self.candidates = candidates
        self.name = name
        self.calls = 0

    def search(self, query: str, limit: int) -> list[ResourceCandidate]:
        del query, limit
        self.calls += 1
        return self.candidates


class PermissiveResolver(ResourceResolver):
    @classmethod
    def is_relevant(cls, candidate: ResourceCandidate, query: str) -> bool:
        del candidate, query
        return True


class LegacyOrderResolver(PermissiveResolver):
    def __init__(
        self,
        providers: list[RecordingProvider],
        ordered: list[ResourceCandidate],
    ) -> None:
        super().__init__(providers)
        self.ordered = ordered

    def resolve(
        self,
        queries: list[str],
        *,
        excluded_urls: set[str] | None = None,
    ) -> list[ResourceCandidate]:
        del queries, excluded_urls
        return self.ordered


class StubResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def candidate(
    *,
    provider: str = "test",
    url: str = "https://en.wikipedia.org/wiki/Intelligent_agent",
    title: str = "Intelligent agent",
    resource_type: str = "article",
) -> ResourceCandidate:
    return ResourceCandidate(
        provider=provider,
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
                title="AI agent engineering walkthrough",
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
        "video",
        "article",
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


def test_video_course_is_returned_before_supporting_articles() -> None:
    article = candidate(
        provider="brave-web",
        url="https://docs.example.com/agents",
        title="AI agent reference guide",
    )
    video = candidate(
        provider="youtube",
        url="https://www.youtube.com/watch?v=course",
        title="AI agents full course",
        resource_type="video",
    )

    resources = ResourceResolver(
        [
            RecordingProvider([article], name="brave-web"),
            RecordingProvider([video], name="youtube"),
        ]
    ).resolve(["AI agent engineering practical tutorial"])

    assert [resource.resource_type for resource in resources] == ["video", "article"]


def test_resolver_excludes_the_current_resource_set() -> None:
    first_video = candidate(
        provider="youtube",
        url="https://www.youtube.com/watch?v=first",
        title="AI agent full course",
        resource_type="video",
    )
    next_video = candidate(
        provider="youtube",
        url="https://www.youtube.com/watch?v=next",
        title="AI agent project tutorial",
        resource_type="video",
    )
    resolver = ResourceResolver(
        [RecordingProvider([first_video, next_video], name="youtube")]
    )

    resources = resolver.resolve(
        ["AI agent engineering practical tutorial"],
        excluded_urls={first_video.url},
    )

    assert [resource.url for resource in resources] == [next_video.url]


def test_refresh_replaces_cached_resources_with_different_urls(client: TestClient) -> None:
    token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, token)
    current_step = steps_in(roadmap)[0]
    first_video = candidate(
        provider="youtube",
        url="https://www.youtube.com/watch?v=first",
        title="AI agent full course",
        resource_type="video",
    )
    next_video = candidate(
        provider="youtube",
        url="https://www.youtube.com/watch?v=next",
        title="AI agent project tutorial",
        resource_type="video",
    )
    provider = RecordingProvider([first_video], name="youtube")
    app.dependency_overrides[get_resource_resolver] = lambda: ResourceResolver([provider])
    initial = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )
    provider.candidates = [first_video, next_video]
    refreshed = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve?refresh=true",
        headers=auth(token),
    )

    assert initial.status_code == refreshed.status_code == 200
    assert [resource["url"] for resource in refreshed.json()["resources"]] == [next_video.url]


def test_not_useful_resource_is_removed_and_never_selected_again(client: TestClient) -> None:
    token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, token)
    current_step = steps_in(roadmap)[0]
    rejected_video = candidate(
        provider="youtube",
        url="https://www.youtube.com/watch?v=rejected",
        title="AI agent full course",
        resource_type="video",
    )
    replacement_video = candidate(
        provider="youtube",
        url="https://www.youtube.com/watch?v=replacement",
        title="Build an AI agent project",
        resource_type="video",
    )
    provider = RecordingProvider([rejected_video], name="youtube")
    app.dependency_overrides[get_resource_resolver] = lambda: ResourceResolver([provider])
    initial = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )

    rejected = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/"
        f"{initial.json()['resources'][0]['id']}/not-useful",
        headers=auth(token),
    )

    provider.candidates = [rejected_video, replacement_video]
    replacement = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )

    assert rejected.status_code == 204
    assert replacement.status_code == 200
    assert [resource["url"] for resource in replacement.json()["resources"]] == [
        replacement_video.url
    ]


def test_not_useful_requires_the_current_step_owner(client: TestClient) -> None:
    owner_token = create_session(client)
    other_token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, owner_token)
    current_step = steps_in(roadmap)[0]
    provider = RecordingProvider(
        [
            candidate(
                provider="youtube",
                url="https://www.youtube.com/watch?v=owner-only",
                title="AI agent full course",
                resource_type="video",
            )
        ],
        name="youtube",
    )
    app.dependency_overrides[get_resource_resolver] = lambda: ResourceResolver([provider])
    initial = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(owner_token),
    )

    response = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/"
        f"{initial.json()['resources'][0]['id']}/not-useful",
        headers=auth(other_token),
    )

    assert response.status_code == 404


def test_refresh_is_limited_per_user_and_step(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        resource_routes,
        "get_settings",
        lambda: Settings(
            resource_alternate_limit_per_step_per_day=1,
            resource_alternate_cooldown_seconds=0,
        ),
    )
    token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, token)
    current_step = steps_in(roadmap)[0]
    first_video = candidate(
        provider="youtube",
        url="https://www.youtube.com/watch?v=first",
        title="AI agent full course",
        resource_type="video",
    )
    next_video = candidate(
        provider="youtube",
        url="https://www.youtube.com/watch?v=next",
        title="AI agent project tutorial",
        resource_type="video",
    )
    provider = RecordingProvider([first_video], name="youtube")
    app.dependency_overrides[get_resource_resolver] = lambda: ResourceResolver([provider])
    client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )
    provider.candidates = [first_video, next_video]
    allowed = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve?refresh=true",
        headers=auth(token),
    )
    blocked = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve?refresh=true",
        headers=auth(token),
    )

    assert allowed.status_code == 200
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "86400"


def test_refresh_has_a_short_server_cooldown(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        resource_routes,
        "get_settings",
        lambda: Settings(
            resource_alternate_limit_per_step_per_day=3,
            resource_alternate_cooldown_seconds=12,
        ),
    )
    token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, token)
    current_step = steps_in(roadmap)[0]
    first_video = candidate(
        provider="youtube",
        url="https://www.youtube.com/watch?v=first",
        title="AI agent full course",
        resource_type="video",
    )
    next_video = candidate(
        provider="youtube",
        url="https://www.youtube.com/watch?v=next",
        title="AI agent project tutorial",
        resource_type="video",
    )
    provider = RecordingProvider([first_video], name="youtube")
    app.dependency_overrides[get_resource_resolver] = lambda: ResourceResolver([provider])
    client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )
    provider.candidates = [first_video, next_video]
    client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve?refresh=true",
        headers=auth(token),
    )
    blocked = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve?refresh=true",
        headers=auth(token),
    )

    assert blocked.status_code == 429
    assert 1 <= int(blocked.headers["retry-after"]) <= 12


def test_video_first_policy_refreshes_old_article_only_cache(client: TestClient) -> None:
    token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, token)
    current_step = steps_in(roadmap)[0]
    article_provider = RecordingProvider([candidate(provider="brave-web")], name="brave-web")
    app.dependency_overrides[get_resource_resolver] = lambda: ResourceResolver([article_provider])
    first = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )
    assert first.json()["resources"][0]["resource_type"] == "article"

    video_provider = RecordingProvider(
        [
            candidate(
                provider="youtube",
                url="https://www.youtube.com/watch?v=course",
                title="AI agent full course",
                resource_type="video",
            )
        ],
        name="youtube",
    )
    app.dependency_overrides[get_resource_resolver] = lambda: ResourceResolver([video_provider])
    refreshed = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )

    assert refreshed.status_code == 200
    assert refreshed.json()["cached"] is False
    assert [resource["resource_type"] for resource in refreshed.json()["resources"]] == ["video"]


def test_video_first_policy_refreshes_cache_when_video_is_not_first(client: TestClient) -> None:
    token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, token)
    current_step = steps_in(roadmap)[0]
    old_article = candidate(provider="brave-web")
    old_video = candidate(
        provider="youtube",
        url="https://www.youtube.com/watch?v=old-video",
        title="AI agent tutorial",
        resource_type="video",
    )
    app.dependency_overrides[get_resource_resolver] = lambda: LegacyOrderResolver(
        [RecordingProvider([], name="brave-web"), RecordingProvider([], name="youtube")],
        [old_article, old_video],
    )
    client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )

    refreshed_provider = RecordingProvider(
        [
            candidate(
                provider="youtube",
                url="https://www.youtube.com/watch?v=primary-video",
                title="AI agent full course",
                resource_type="video",
            )
        ],
        name="youtube",
    )
    app.dependency_overrides[get_resource_resolver] = lambda: ResourceResolver([refreshed_provider])
    refreshed = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )

    assert refreshed.status_code == 200
    assert refreshed.json()["cached"] is False
    assert refreshed.json()["resources"][0]["url"].endswith("primary-video")


def test_unsafe_or_incomplete_candidates_are_not_stored(client: TestClient) -> None:
    token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, token)
    current_step = steps_in(roadmap)[0]
    provider = RecordingProvider(
        [
            candidate(url="http://127.0.0.1/internal"),
            candidate(url="https://localhost/resource"),
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


def test_unrelated_cached_resources_are_rejected(
    client: TestClient,
) -> None:
    token = create_session(client)
    _, roadmap = create_accepted_roadmap(client, token)
    current_step = steps_in(roadmap)[0]
    unrelated = candidate(
        provider="wikipedia",
        title="Robert Englund",
        url="https://en.wikipedia.org/wiki/Robert_Englund",
    )
    provider = RecordingProvider([unrelated], name="wikipedia")
    app.dependency_overrides[get_resource_resolver] = lambda: PermissiveResolver([provider])
    stored = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )
    assert stored.json()["available"] is True

    app.dependency_overrides[get_resource_resolver] = lambda: ResourceResolver([provider])
    cleaned = client.post(
        f"/api/v1/roadmap-steps/{current_step['id']}/resources/resolve",
        headers=auth(token),
    )

    assert cleaned.status_code == 200
    assert cleaned.json()["available"] is False
    assert cleaned.json()["resources"] == []


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


def test_youtube_provider_uses_search_then_current_video_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict] = []

    def fake_get(url: str, **kwargs: object) -> StubResponse:
        requests.append({"url": url, **kwargs})
        if url == YouTubeResourceProvider.search_endpoint:
            return StubResponse({"items": [{"id": {"videoId": "agent-video"}}]})
        return StubResponse(
            {
                "items": [
                    {
                        "id": "agent-video",
                        "snippet": {
                            "title": "Build reliable AI agents",
                            "channelTitle": "Engineering Academy",
                            "publishedAt": "2026-05-01T00:00:00Z",
                            "thumbnails": {
                                "high": {"url": "https://i.ytimg.com/vi/agent-video/hqdefault.jpg"}
                            },
                        },
                        "statistics": {"viewCount": "250000"},
                        "contentDetails": {"duration": "PT1H10M"},
                        "status": {"privacyStatus": "public"},
                    }
                ]
            }
        )

    monkeypatch.setattr("app.resources.providers.httpx.get", fake_get)
    resources = YouTubeResourceProvider("test-key", 2).search("AI agent engineering", 2)

    assert [request["url"] for request in requests] == [
        YouTubeResourceProvider.search_endpoint,
        YouTubeResourceProvider.videos_endpoint,
    ]
    assert requests[0]["params"]["key"] == "test-key"
    assert requests[0]["params"]["q"].endswith("full course practical tutorial")
    assert resources[0].title == "Build reliable AI agents"
    assert resources[0].source_name == "Engineering Academy"
    assert resources[0].resource_type == "video"
    assert resources[0].quality_score > 0
    assert "1h 10m" in resources[0].description
    assert resources[0].verified_at is not None


def test_brave_provider_excludes_wikipedia_and_preserves_source_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(url: str, **kwargs: object) -> StubResponse:
        assert url == BraveSearchResourceProvider.endpoint
        assert kwargs["headers"]["X-Subscription-Token"] == "test-key"
        return StubResponse(
            {
                "web": {
                    "results": [
                        {
                            "title": "AI Agent Course",
                            "url": "https://www.freecodecamp.org/news/ai-agent-course/",
                            "description": "A practical AI agent engineering course.",
                            "profile": {"long_name": "freeCodeCamp"},
                        },
                        {
                            "title": "AI agent",
                            "url": "https://en.wikipedia.org/wiki/Intelligent_agent",
                            "description": "Excluded background article.",
                        },
                    ]
                }
            }
        )

    monkeypatch.setattr("app.resources.providers.httpx.get", fake_get)
    resources = BraveSearchResourceProvider("test-key", 2).search("AI agent engineering", 2)

    assert len(resources) == 1
    assert resources[0].source_name == "freeCodeCamp"
    assert resources[0].resource_type == "article"
    assert resources[0].quality_score == 0.9
