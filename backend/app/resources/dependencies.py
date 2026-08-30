from functools import lru_cache

from app.core.config import get_settings
from app.resources.providers import CuratedVideoProvider, WikipediaResourceProvider
from app.resources.service import ResourceResolver


@lru_cache
def get_resource_resolver() -> ResourceResolver:
    settings = get_settings()
    timeout = settings.resource_request_timeout_seconds
    return ResourceResolver(
        providers=[
            CuratedVideoProvider(timeout),
            WikipediaResourceProvider(timeout),
        ],
        max_results=settings.resource_max_results_per_step,
    )
