import asyncio
import logging
from datetime import datetime
from typing import List

import aiohttp

from models.news_item import NewsItem
from .base import BaseCrawler

logger = logging.getLogger(__name__)


class NewsAPICrawler(BaseCrawler):
    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str, query: str, page_size: int = 100) -> None:
        self.api_key = api_key
        self.query = query
        self.page_size = page_size
        self.source = "newsapi"

    async def _request(self, session: aiohttp.ClientSession, page: int) -> dict:
        params = {
            "q": self.query,
            "apiKey": self.api_key,
            "page": page,
            "pageSize": self.page_size,
            "language": "en",
        }
        async with session.get(self.BASE_URL, params=params) as resp:
            if resp.status == 429:
                retry_after = int(resp.headers.get("Retry-After", 1))
                logger.warning("Rate limited. Sleeping for %s", retry_after)
                await asyncio.sleep(retry_after)
                return await self._request(session, page)
            resp.raise_for_status()
            return await resp.json()

    async def fetch_new(self) -> List[NewsItem]:
        return await self.fetch_recent(24)

    async def fetch_recent(self, lookback_hours: int) -> List[NewsItem]:
        async with aiohttp.ClientSession() as session:
            page = 1
            items = []
            while True:
                data = await self._request(session, page)
                for article in data.get("articles", []):
                    items.append(self._normalize(article))
                if page * self.page_size >= data.get("totalResults", 0):
                    break
                page += 1
            logger.info("Fetched %d items from NewsAPI", len(items))
            return items

    async def fetch_by_date(self, start: datetime, end: datetime) -> List[NewsItem]:
        # NewsAPI supports from/to params
        async with aiohttp.ClientSession() as session:
            params = {
                "q": self.query,
                "apiKey": self.api_key,
                "from": start.isoformat(),
                "to": end.isoformat(),
                "pageSize": self.page_size,
            }
            async with session.get(self.BASE_URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()
        return [self._normalize(a) for a in data.get("articles", [])]

    def _normalize(self, raw_data) -> NewsItem:
        published_str = raw_data.get("publishedAt")
        dt = datetime.fromisoformat(published_str.rstrip("Z")) if published_str else datetime.utcnow()
        return NewsItem(
            title=raw_data.get("title", ""),
            url=raw_data.get("url", ""),
            source="newsapi",
            publish_date=dt,
            summary=raw_data.get("description"),
            full_text=raw_data.get("content"),
            meta={"source": raw_data.get("source", {}).get("name")}
        )
