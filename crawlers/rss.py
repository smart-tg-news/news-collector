import logging
from datetime import datetime
from typing import List
from dataclasses import asdict
import json

import aiohttp
import feedparser

from models.news_item import NewsItem
from db.client import MongoClientSingleton
from .base import BaseCrawler


logger = logging.getLogger(__name__)


class RSSCrawler(BaseCrawler):
    def __init__(self, feed_url: str, state_path: str = "rss_state.db") -> None:
        self.feed_url = feed_url
        self.state_path = state_path
        self.source = feed_url

    async def _fetch_feed(self) -> feedparser.FeedParserDict:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.feed_url) as resp:
                resp.raise_for_status()
                text = await resp.text()
        return feedparser.parse(text)

    async def fetch_new(self) -> List[NewsItem]:
        feed = await self._fetch_feed()
        items = []
        for entry in feed.entries:
            items.append(self._normalize(entry))
        logger.info("Fetched %d items", len(items))
        return items

    async def fetch_recent(self, lookback_hours: int) -> List[NewsItem]:
        feed = await self._fetch_feed()
        cutoff = datetime.now().timestamp() - lookback_hours * 3600
        items = [self._normalize(e) for e in feed.entries if e.published_parsed and datetime(*e.published_parsed[:6]).timestamp() >= cutoff]
        return items

    async def fetch_by_date(self, start: datetime, end: datetime) -> List[NewsItem]:
        feed = await self._fetch_feed()
        items = []
        for entry in feed.entries:
            if not entry.published_parsed:
                continue
            dt = datetime(*entry.published_parsed[:6])
            if start <= dt <= end:
                items.append(self._normalize(entry))
        return items

    def save_data(self, data: List[NewsItem]) -> None:
        mongo_client = MongoClientSingleton()
        database = mongo_client["Prod"]
        collection = database["news_raw"]

        dict_data = [asdict(entry) for entry in data]
        collection.insert_many(dict_data)
        logger.info(f"Saved {len(dict_data)} news to db")

    def _normalize(self, raw_data) -> NewsItem:
        published = raw_data.published_parsed
        dt = datetime(*published[:6]) if published else datetime.now()
        return NewsItem(
            title=raw_data.get("title", ""),
            url=raw_data.get("link", ""),
            source=self.feed_url,
            publish_date=dt,
            summary=raw_data.get("summary"),
            meta={"id": raw_data.get("id")}
        )
    
    @staticmethod
    def feed_to_json(feed):
        return json.dumps(feed, indent=2, ensure_ascii=False)
