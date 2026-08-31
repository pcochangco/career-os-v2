from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ResourceCandidate:
    provider: str
    resource_type: str
    title: str
    url: str
    source_name: str
    description: str
    why_relevant: str
    thumbnail_url: str
    verified_at: datetime
    quality_score: float = 0.0
