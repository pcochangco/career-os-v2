from __future__ import annotations

import ipaddress
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from app.resources.providers import ResourceProvider, ResourceProviderError
from app.resources.schema import ResourceCandidate


class ResourceResolver:
    generic_query_words = {
        "beginner",
        "build",
        "capstone",
        "complete",
        "concepts",
        "create",
        "essential",
        "framework",
        "guide",
        "how",
        "ideas",
        "learn",
        "master",
        "portfolio",
        "practical",
        "practice",
        "present",
        "project",
        "roadmap",
        "rubric",
        "the",
        "to",
        "tutorial",
        "work",
    }
    allowed_thumbnail_hosts = {
        "i.ytimg.com",
    }

    def __init__(
        self,
        providers: list[ResourceProvider],
        max_results: int = 3,
        cache_ttl_hours: int = 168,
    ) -> None:
        self.providers = providers
        self.max_results = max_results
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.provider_names = {provider.name for provider in providers}

    def resolve(
        self,
        queries: list[str],
        *,
        excluded_urls: set[str] | None = None,
    ) -> list[ResourceCandidate]:
        excluded_urls = excluded_urls or set()
        candidates_by_url: dict[str, ResourceCandidate] = {}
        for query in queries[:3]:
            clean_query = " ".join(query.split())[:300]
            if not clean_query:
                continue
            for provider in self.providers:
                try:
                    candidates = provider.search(clean_query, self.max_results)
                except ResourceProviderError:
                    continue
                for candidate in candidates:
                    if candidate.url in excluded_urls:
                        continue
                    if not self.is_safe(candidate) or not self.is_relevant(candidate, clean_query):
                        continue
                    existing = candidates_by_url.get(candidate.url)
                    if existing is None or self.rank(candidate, clean_query) > self.rank(
                        existing, clean_query
                    ):
                        candidates_by_url[candidate.url] = candidate
        ranked = sorted(
            candidates_by_url.values(),
            key=lambda candidate: self.rank(candidate, " ".join(queries)),
            reverse=True,
        )
        # A learner should have a practical starting point first. Articles remain useful
        # supporting material, but should not crowd out an available course or tutorial.
        videos = [candidate for candidate in ranked if candidate.resource_type == "video"]
        supporting = [candidate for candidate in ranked if candidate.resource_type != "video"]
        if not videos:
            return supporting[: self.max_results]
        return (videos + supporting)[: self.max_results]

    @classmethod
    def is_relevant(cls, candidate: ResourceCandidate, query: str) -> bool:
        return cls.is_relevant_text(
            provider=candidate.provider,
            query=query,
            title=candidate.title,
            description=candidate.description,
        )

    @classmethod
    def is_relevant_text(
        cls,
        *,
        provider: str,
        query: str,
        title: str,
        description: str,
    ) -> bool:
        topic_tokens = cls.topic_tokens(query)
        if not topic_tokens:
            return True
        content_tokens = cls.normalized_tokens(f"{title} {description}")
        return bool(topic_tokens & content_tokens)

    @classmethod
    def rank(cls, candidate: ResourceCandidate, query: str) -> float:
        topic_tokens = cls.topic_tokens(query)
        content_tokens = cls.normalized_tokens(f"{candidate.title} {candidate.description}")
        overlap = len(topic_tokens & content_tokens) / max(len(topic_tokens), 1)
        source_bonus = 0.35 if candidate.resource_type == "video" else 0.0
        return candidate.quality_score + overlap + source_bonus

    @property
    def has_video_provider(self) -> bool:
        return "youtube" in self.provider_names

    @classmethod
    def topic_tokens(cls, value: str) -> set[str]:
        return cls.normalized_tokens(value) - cls.generic_query_words

    @staticmethod
    def normalized_tokens(value: str) -> set[str]:
        tokens = set(re.findall(r"[a-z0-9+#.]+", value.lower()))
        return tokens | {
            token[:-1]
            for token in tokens
            if token.endswith("s") and len(token) > 4
        }

    def is_safe(self, candidate: ResourceCandidate) -> bool:
        parsed = urlparse(candidate.url)
        thumbnail = urlparse(candidate.thumbnail_url) if candidate.thumbnail_url else None
        return bool(
            candidate.resource_type in {"article", "video"}
            and candidate.provider in self.provider_names
            and candidate.title.strip()
            and candidate.source_name.strip()
            and parsed.scheme == "https"
            and self.is_public_hostname(parsed.hostname)
            and len(candidate.title) <= 300
            and len(candidate.url) <= 2048
            and (
                thumbnail is None
                or (
                    thumbnail.scheme == "https"
                    and thumbnail.hostname in self.allowed_thumbnail_hosts
                    and len(candidate.thumbnail_url) <= 2048
                )
            )
            and len(candidate.source_name) <= 160
        )

    def is_cached_resource_acceptable(
        self,
        *,
        provider: str,
        verified_at: datetime,
        title: str,
        description: str,
        queries: list[str],
    ) -> bool:
        if provider not in self.provider_names or not self.is_fresh(verified_at):
            return False
        return any(
            self.is_relevant_text(
                provider=provider, query=query, title=title, description=description
            )
            for query in queries
        )

    def is_fresh(self, verified_at: datetime) -> bool:
        normalized = verified_at if verified_at.tzinfo else verified_at.replace(tzinfo=UTC)
        return normalized >= datetime.now(UTC) - self.cache_ttl

    @staticmethod
    def is_public_hostname(hostname: str | None) -> bool:
        if not hostname:
            return False
        normalized = hostname.lower().rstrip(".")
        if normalized == "localhost" or normalized.endswith(".local"):
            return False
        try:
            return not ipaddress.ip_address(normalized).is_private
        except ValueError:
            return True
