from functools import lru_cache

from app.core.config import get_settings
from app.resources.providers import BraveSearchResourceProvider, YouTubeResourceProvider
from app.resources.service import ResourceResolver


@lru_cache
def get_resource_resolver() -> ResourceResolver:
    settings = get_settings()
    timeout = settings.resource_request_timeout_seconds
    providers = []
    if settings.youtube_api_configured:
        providers.append(
            YouTubeResourceProvider(settings.youtube_api_key.get_secret_value(), timeout)
        )
    if settings.brave_search_api_configured:
        providers.append(
            BraveSearchResourceProvider(settings.brave_search_api_key.get_secret_value(), timeout)
        )
    return ResourceResolver(
        providers=providers,
        max_results=settings.resource_max_results_per_step,
        cache_ttl_hours=settings.resource_cache_ttl_hours,
    )
