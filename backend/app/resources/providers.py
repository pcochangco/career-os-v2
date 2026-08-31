from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from app.resources.schema import ResourceCandidate


class ResourceProviderError(RuntimeError):
    """A retrieval provider could not return verified results."""


class ResourceProvider(Protocol):
    name: str

    def search(self, query: str, limit: int) -> list[ResourceCandidate]: ...


class YouTubeResourceProvider:
    """Find public learning videos and enrich them with current YouTube metadata."""

    name = "youtube"
    search_endpoint = "https://www.googleapis.com/youtube/v3/search"
    videos_endpoint = "https://www.googleapis.com/youtube/v3/videos"

    def __init__(self, api_key: str, timeout_seconds: float) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, limit: int) -> list[ResourceCandidate]:
        try:
            search_response = httpx.get(
                self.search_endpoint,
                params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "order": "relevance",
                    "videoEmbeddable": "true",
                    "safeSearch": "strict",
                    "maxResults": min(max(limit * 4, 6), 18),
                    "key": self.api_key,
                },
                timeout=self.timeout_seconds,
            )
            search_response.raise_for_status()
            search_items = search_response.json().get("items", [])
            if not isinstance(search_items, list):
                raise TypeError("Unexpected YouTube search response")
            video_ids = [
                item.get("id", {}).get("videoId")
                for item in search_items
                if isinstance(item, dict) and isinstance(item.get("id"), dict)
            ]
            video_ids = [
                video_id for video_id in video_ids if isinstance(video_id, str) and video_id
            ]
            if not video_ids:
                return []
            details_response = httpx.get(
                self.videos_endpoint,
                params={
                    "part": "snippet,contentDetails,statistics,status",
                    "id": ",".join(video_ids),
                    "key": self.api_key,
                },
                timeout=self.timeout_seconds,
            )
            details_response.raise_for_status()
            details = details_response.json().get("items", [])
            if not isinstance(details, list):
                raise TypeError("Unexpected YouTube video response")
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise ResourceProviderError("YouTube retrieval failed") from error

        verified_at = datetime.now(UTC)
        resources: list[ResourceCandidate] = []
        for item in details:
            if (
                not isinstance(item, dict)
                or item.get("status", {}).get("privacyStatus") != "public"
            ):
                continue
            snippet = item.get("snippet")
            statistics = item.get("statistics")
            if not isinstance(snippet, dict) or not isinstance(statistics, dict):
                continue
            video_id = item.get("id")
            title = str(snippet.get("title", "")).strip()
            channel = str(snippet.get("channelTitle", "YouTube")).strip()
            if not isinstance(video_id, str) or not title or not channel:
                continue
            thumbnails = snippet.get("thumbnails")
            thumbnail_url = ""
            if isinstance(thumbnails, dict):
                for size in ("high", "medium", "default"):
                    value = thumbnails.get(size)
                    if isinstance(value, dict) and isinstance(value.get("url"), str):
                        thumbnail_url = value["url"].strip()
                        break
            views = self._int_value(statistics.get("viewCount"))
            published_at = self._parse_datetime(snippet.get("publishedAt"))
            duration = str(item.get("contentDetails", {}).get("duration", "")).strip()
            published_label = published_at.strftime("%Y") if published_at else "recently"
            details_label = f"{self._view_label(views)} views · Published {published_label}"
            if duration:
                details_label = f"{details_label} · {duration.removeprefix('PT').lower()}"
            resources.append(
                ResourceCandidate(
                    provider=self.name,
                    resource_type="video",
                    title=title,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    source_name=channel,
                    description=details_label,
                    why_relevant=(
                        f"A public learning video from {channel}, selected using its topic match, "
                        "current metadata, and audience reach."
                    ),
                    thumbnail_url=thumbnail_url,
                    verified_at=verified_at,
                    quality_score=self._quality_score(views, published_at),
                )
            )
        return resources

    @staticmethod
    def _int_value(value: Any) -> int:
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _view_label(views: int) -> str:
        if views >= 1_000_000:
            return f"{views / 1_000_000:.1f}M"
        if views >= 1_000:
            return f"{views / 1_000:.0f}K"
        return str(views)

    @staticmethod
    def _quality_score(views: int, published_at: datetime | None) -> float:
        popularity = min(math.log10(views + 1) / 7, 1.0) * 0.55
        if published_at is None:
            return popularity + 0.15
        age_days = max((datetime.now(UTC) - published_at).days, 0)
        freshness = 0.35 if age_days <= 365 else 0.28 if age_days <= 1_095 else 0.18
        return popularity + freshness


class BraveSearchResourceProvider:
    """Retrieve current articles, official guidance, free courses, and community context."""

    name = "brave-web"
    endpoint = "https://api.search.brave.com/res/v1/web/search"
    excluded_hosts = {"en.wikipedia.org", "wikipedia.org", "m.wikipedia.org"}
    trusted_domains = {
        "freecodecamp.org",
        "cs50.harvard.edu",
        "fullstackopen.com",
        "roadmap.sh",
        "developer.mozilla.org",
        "docs.python.org",
        "fastapi.tiangolo.com",
        "europa.eu",
        "erasmus-plus.ec.europa.eu",
    }

    def __init__(self, api_key: str, timeout_seconds: float) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, limit: int) -> list[ResourceCandidate]:
        try:
            response = httpx.get(
                self.endpoint,
                params={
                    "q": query,
                    "count": min(max(limit * 4, 6), 20),
                    "search_lang": "en",
                    "safesearch": "moderate",
                    "extra_snippets": "true",
                },
                headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            results = response.json().get("web", {}).get("results", [])
            if not isinstance(results, list):
                raise TypeError("Unexpected Brave Search response")
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise ResourceProviderError("Web search retrieval failed") from error

        verified_at = datetime.now(UTC)
        resources: list[ResourceCandidate] = []
        for result in results:
            if not isinstance(result, dict):
                continue
            url = str(result.get("url", "")).strip()
            hostname = (urlparse(url).hostname or "").lower()
            if not url or hostname in self.excluded_hosts or hostname.endswith(".wikipedia.org"):
                continue
            title = str(result.get("title", "")).strip()
            description = str(result.get("description", "")).strip()
            profile = result.get("profile")
            source_name = (
                str(profile.get("long_name", "")).strip()
                if isinstance(profile, dict)
                else ""
            ) or hostname.removeprefix("www.")
            if not title or not source_name:
                continue
            resources.append(
                ResourceCandidate(
                    provider=self.name,
                    resource_type="article",
                    title=title,
                    url=url,
                    source_name=source_name,
                    description=description[:900],
                    why_relevant=(
                        "A current web result selected for its topic match and source quality."
                    ),
                    thumbnail_url="",
                    verified_at=verified_at,
                    quality_score=self._quality_score(hostname),
                )
            )
        return resources

    def _quality_score(self, hostname: str) -> float:
        bare_host = hostname.removeprefix("www.")
        if bare_host in self.trusted_domains or any(
            bare_host.endswith(f".{domain}") for domain in self.trusted_domains
        ):
            return 0.9
        if bare_host.endswith(".gov") or bare_host.endswith(".edu") or ".gov." in bare_host:
            return 0.85
        if bare_host.endswith("reddit.com"):
            return 0.55
        if bare_host.startswith("docs."):
            return 0.8
        return 0.65
