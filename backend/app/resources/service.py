from __future__ import annotations

from urllib.parse import urlparse

from app.resources.providers import ResourceProvider, ResourceProviderError
from app.resources.schema import ResourceCandidate


class ResourceResolver:
    allowed_hosts = {
        "en.wikipedia.org",
        "www.youtube.com",
        "youtube.com",
        "youtu.be",
    }
    allowed_thumbnail_hosts = {
        "i.ytimg.com",
        "upload.wikimedia.org",
    }

    def __init__(self, providers: list[ResourceProvider], max_results: int = 3) -> None:
        self.providers = providers
        self.max_results = max_results

    def resolve(self, queries: list[str]) -> list[ResourceCandidate]:
        accepted: list[ResourceCandidate] = []
        seen_urls: set[str] = set()
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
                    if not self.is_safe(candidate) or candidate.url in seen_urls:
                        continue
                    accepted.append(candidate)
                    seen_urls.add(candidate.url)
                    if len(accepted) >= self.max_results:
                        return accepted
        return accepted

    @classmethod
    def is_safe(cls, candidate: ResourceCandidate) -> bool:
        parsed = urlparse(candidate.url)
        thumbnail = urlparse(candidate.thumbnail_url) if candidate.thumbnail_url else None
        return bool(
            candidate.resource_type in {"article", "video"}
            and candidate.title.strip()
            and candidate.source_name.strip()
            and parsed.scheme == "https"
            and parsed.hostname in cls.allowed_hosts
            and len(candidate.title) <= 300
            and len(candidate.url) <= 2048
            and (
                thumbnail is None
                or (
                    thumbnail.scheme == "https"
                    and thumbnail.hostname in cls.allowed_thumbnail_hosts
                    and len(candidate.thumbnail_url) <= 2048
                )
            )
            and len(candidate.source_name) <= 160
        )
