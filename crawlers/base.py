import abc
from typing import List
from datetime import datetime

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
    def _normalize(self, raw_data) -> NewsItem:
        """Convert raw response to NewsItem"""
