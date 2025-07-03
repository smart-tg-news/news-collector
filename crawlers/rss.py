import logging
import shelve
from datetime import datetime
from typing import List

import aiohttp
import feedparser

from models.news_item import NewsItem
from .base import BaseCrawler


logger = logging.getLogger(__name__)


class RSSCrawler(BaseCrawler):
    def __init__(self, feed_url: str, state_path: str = "rss_state.db") -> None:
        self.feed_url = feed_url
        self.state_path = state_path
        self.source = feed_url

    def _load_last_id(self) -> str:
        with shelve.open(self.state_path) as db:
            return db.get(self.feed_url, "")

    def _save_last_id(self, entry_id: str) -> None:
        with shelve.open(self.state_path) as db:
            db[self.feed_url] = entry_id

    async def _fetch_feed(self) -> feedparser.FeedParserDict:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.feed_url) as resp:
                resp.raise_for_status()
                text = await resp.text()
        return feedparser.parse(text)

    async def fetch_new(self) -> List[NewsItem]:
        feed = await self._fetch_feed()
        last_id = self._load_last_id()
        items = []
        for entry in feed.entries:
            if last_id and entry.id == last_id:
                break
            items.append(self._normalize(entry))
        if feed.entries:
            self._save_last_id(feed.entries[0].id)
        logger.info("Fetched %d new items", len(items))
        return items

    async def fetch_recent(self, lookback_hours: int) -> List[NewsItem]:
        feed = await self._fetch_feed()
        cutoff = datetime.utcnow().timestamp() - lookback_hours * 3600
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

    def _normalize(self, raw_data) -> NewsItem:
        published = raw_data.published_parsed
        dt = datetime(*published[:6]) if published else datetime.utcnow()
        return NewsItem(
            title=raw_data.get("title", ""),
            url=raw_data.get("link", ""),
            source=self.feed_url,
            publish_date=dt,
            summary=raw_data.get("summary"),
            meta={"id": raw_data.get("id")}
        )
