import abc
from typing import List
from datetime import datetime
import json
from dataclasses import asdict

from models.news_item import NewsItem


class BaseCrawler(abc.ABC):
    source: str

    @abc.abstractmethod
    async def fetch_new(self) -> List[NewsItem]:
        """Return only new news items"""

    @abc.abstractmethod
    async def fetch_recent(self, lookback_hours: int) -> List[NewsItem]:
        """Return news from the last `lookback_hours`"""

    @abc.abstractmethod
    async def fetch_by_date(self, start: datetime, end: datetime) -> List[NewsItem]:
        """Return news items published between start and end"""

    @abc.abstractmethod
    def save_data(self, data) -> None:
        """Store collected news items"""

    @abc.abstractmethod
    def _normalize(self, raw_data) -> NewsItem:
        """Convert raw response to NewsItem"""

    def normalize_entries(self, entries):
        normalised_entries = []
        for entry in entries:
            normalized_entry = self._normalize(entry)
            if normalized_entry:
                normalised_entries.append(normalized_entry)
        return normalised_entries

    @staticmethod
    def news_to_json(news: List[NewsItem]) -> str:
        news_dict = [asdict(entry) for entry in news]
        return json.dumps(news_dict, indent=2, default=str)
