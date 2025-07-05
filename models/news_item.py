from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NewsItem:
    title: str
    url: str
    publish_date: datetime
    summary: Optional[str] = None
    full_text: Optional[str] = None
    meta: dict = field(default_factory=dict)
