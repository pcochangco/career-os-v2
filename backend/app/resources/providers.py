from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

import httpx

from app.resources.schema import ResourceCandidate


class ResourceProviderError(RuntimeError):
    """A retrieval provider could not return verified results."""


class ResourceProvider(Protocol):
    def search(self, query: str, limit: int) -> list[ResourceCandidate]: ...


class WikipediaResourceProvider:
    endpoint = "https://en.wikipedia.org/w/api.php"
    intent_phrases = (
        "competency framework beginner guide",
        "essential concepts roadmap",
        "complete practical tutorial",
        "practice project ideas",
        "capstone project rubric",
        "portfolio work",
    )

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, limit: int) -> list[ResourceCandidate]:
        topic_query = query
        for phrase in self.intent_phrases:
            topic_query = topic_query.replace(phrase, "")
        topic_query = topic_query.removeprefix("how to present ").strip() or query
        try:
            response = httpx.get(
                self.endpoint,
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrlimit": min(limit, 3),
                    "gsrnamespace": 0,
                    "gsrsearch": topic_query,
                    "prop": "extracts|info",
                    "exchars": 320,
                    "exintro": 1,
                    "explaintext": 1,
                    "inprop": "url",
                    "format": "json",
                    "formatversion": 2,
                },
                headers={
                    "User-Agent": (
                        "CareerOS/0.1 (https://github.com/pcochangco/career-os-v2)"
                    )
                },
                follow_redirects=True,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            pages = response.json().get("query", {}).get("pages", [])
            if not isinstance(pages, list):
                raise TypeError("Unexpected Wikipedia response")
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise ResourceProviderError("Wikipedia retrieval failed") from error

        verified_at = datetime.now(UTC)
        return [
            ResourceCandidate(
                provider="wikipedia",
                resource_type="article",
                title=str(page.get("title", "")).strip(),
                url=str(page.get("fullurl", "")).strip(),
                source_name="Wikipedia",
                description=str(page.get("extract", "")).strip(),
                why_relevant=f'Background reading related to “{query}”.',
                thumbnail_url="",
                verified_at=verified_at,
            )
            for page in pages
            if isinstance(page, dict)
        ]


class CuratedVideoProvider:
    videos = (
        {
            "keywords": {"practice", "project", "tutorial", "workflow", "learn"},
            "url": "https://www.youtube.com/watch?v=f2O6mQkFiiw",
            "why_relevant": (
                "A short evidence-based guide to making practice deliberate and effective."
            ),
        },
        {
            "keywords": {"present", "portfolio", "explain", "package", "share"},
            "url": "https://www.youtube.com/watch?v=Unzc731iCUY",
            "why_relevant": (
                "A practical lecture on explaining complex work clearly and memorably."
            ),
        },
    )

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, limit: int) -> list[ResourceCandidate]:
        words = {word.strip(".,:;!?()[]{}\"").lower() for word in query.split()}
        matches = [video for video in self.videos if words & video["keywords"]]
        results: list[ResourceCandidate] = []
        for video in matches[:limit]:
            try:
                response = httpx.get(
                    "https://www.youtube.com/oembed",
                    params={"url": video["url"], "format": "json"},
                    headers={
                        "User-Agent": (
                            "CareerOS/0.1 (https://github.com/pcochangco/career-os-v2)"
                        )
                    },
                    follow_redirects=True,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError, TypeError):
                continue
            results.append(
                ResourceCandidate(
                    provider="curated-youtube",
                    resource_type="video",
                    title=str(payload.get("title", "")).strip(),
                    url=str(video["url"]),
                    source_name=str(payload.get("author_name", "YouTube")).strip(),
                    description="Curated learning video with metadata verified through YouTube.",
                    why_relevant=str(video["why_relevant"]),
                    thumbnail_url=str(payload.get("thumbnail_url", "")).strip(),
                    verified_at=datetime.now(UTC),
                )
            )
        return results
