import logging
from datetime import datetime
from typing import List, Optional
from dataclasses import asdict
from collections import defaultdict
import json

import aiohttp
import feedparser

from models.news_item import NewsItem
from db.client import MongoClientSingleton
from ..base import BaseCrawler
from .extra_field_processors import Processor
from .filter import FilterStrategy


logger = logging.getLogger(__name__)


class RSSCrawler(BaseCrawler):
    def __init__(
            self, 
            feed_url: str, 
            filter_strategy: Optional[FilterStrategy] = None,
            processors: Optional[List[Processor]] = None
    ) -> None:
        
        self.feed_url = feed_url
        self.source = feed_url
        self.filter_strategy = filter_strategy
        self.processors = processors or []

    async def _fetch_feed(self) -> feedparser.FeedParserDict:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.feed_url) as resp:
                resp.raise_for_status()
                text = await resp.text()
        return feedparser.parse(text)

    async def fetch_new(self) -> List[NewsItem]:
        feed = await self._fetch_feed()
        logger.info("Fetched %d items", len(feed.entries))
        
        # with open("/home/koldi/se/news-collector/feed_samples/feed_techcrunch.json", 'w') as f:
        #     f.write(self.feed_to_json(feed))

        # different filter logic for different feeds
        filtered_feed_entries = feed.entries
        if (self.filter_strategy is not None) and (feed.entries):
            filtered_feed_entries = await self.filter_strategy.filter_new(feed, self.feed_url)
        logger.info("Left %d items after filtering", len(filtered_feed_entries))

        items = []
        for entry in filtered_feed_entries:
            items.append(self._normalize(entry))
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
        if dict_data:
            collection.insert_many(dict_data)
        logger.info(f"Saved {len(dict_data)} news to db")
    
    def _normalize(self, raw_data) -> NewsItem:
        published = raw_data.published_parsed
        publish_date = datetime(*published[:6]) if published else datetime.now()

        # base fields, present in all feeds
        processed_data = {}
        processed_data["title"]        = raw_data.get("title", "")
        processed_data["url"]          = raw_data.get("link", "")
        processed_data["summary"]      = raw_data.get("summary")
        processed_data["publish_date"] = publish_date
        processed_data["full_text"]    = str()
        # if new fields are defined, put them inside meta
        processed_data["meta"]         = dict()  

        # call proccessors to fill extra fields in processed data
        for proc in self.processors:
            proc(raw_data, processed_data)

        return NewsItem(**processed_data)
    
    @staticmethod
    def feed_to_json(feed):
        return json.dumps(feed, indent=2, ensure_ascii=False)
