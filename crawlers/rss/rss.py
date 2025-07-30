import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import asdict
import json
import trafilatura

import aiohttp
import asyncio
import feedparser

from models.news_item import NewsItem
from db.client import MongoClientSingleton
from utils.http_session import get_shared_session
from utils.trafilatura import get_trafilatura_config
from utils.config import cfg
from ..base import BaseCrawler
from .extra_field_processors import Processor
from .filter import FilterStrategy


logger = logging.getLogger(__name__)

trafilatura_conf =  get_trafilatura_config()


class FetchException(Exception):
    ...
    

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
        self.session = get_shared_session()

    async def _fetch_feed(self, max_retries: int = 3, backoff: float = 4.0) -> feedparser.FeedParserDict:

        for attempt in range(1, max_retries + 1):
            try:
                async with self.session.get(self.feed_url) as resp:
                    resp.raise_for_status()
                    text = await resp.text()

                feed = feedparser.parse(text)  
                if feed.bozo:
                    bad_exc = feed.bozo_exception
                    raise FetchException(f"Feed parse error ({bad_exc})")
                return feed
            
            except asyncio.TimeoutError as e:         # timeout
                logger.warning(f"Timeout fetching feed {self.feed_url}, request took too long")

            except aiohttp.ClientConnectionError as e: # e.g. DNS lookup failed, refused connection
                logger.warning(f"Connection failed for feed {self.feed_url}")
            
            except aiohttp.ClientResponseError as e:  # HTTP-level error (4xx, 5xx)
                if e.status != 429:  # only retryable status code
                    raise FetchException( 
                        f"HTTP {e.status} {e.message or e.request_info.real_url}"
                    ) from e
                else:
                    logger.warning(f"Too many requests 429 when fetching {self.feed_url}")
            
            except aiohttp.ClientError as e:           # all other client‑side errors
                raise FetchException(f"Client error ({e})") from e
            
            except Exception:                          # all other exceptions
                raise
            
            if attempt < max_retries:
                await asyncio.sleep(backoff)
                backoff *= 2


    async def fetch_new(self) -> List[NewsItem]:
        try:
            feed = await self._fetch_feed()
        except FetchException as e:
            logger.warning(f"Error fetching feed for {self.feed_url}: {e}")
            raise FetchException
        logger.info(f"Fetched {len(feed.entries)} items for {self.feed_url}")
        
        # with open("/home/koldi/se/news-collector/feed_samples/nypost.json", 'w') as f:
        #     f.write(self.feed_to_json(feed))

        # different filter logic for different feeds
        filtered_feed_entries = feed.entries
        if (self.filter_strategy is not None) and (feed.entries):
            filtered_feed_entries = await self.filter_strategy.filter_new(feed, self.feed_url)

        items = []
        for entry in filtered_feed_entries:
            normalized_entry = self._normalize(entry)
            if normalized_entry:
                items.append(normalized_entry)

        if len(items) < len(filtered_feed_entries) // 2:
            logger.warning(f"Wasn't able to normalize enough entries from {self.feed_url}")
            raise FetchException
            
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
        database = mongo_client[cfg.mongo_db]
        collection = database[cfg.mongo_table]

        dict_data = [asdict(entry) for entry in data]
        if dict_data:
            collection.insert_many(dict_data)
        logger.info(f"Saved {len(dict_data)} news to db for {self.feed_url}")
    
    def _normalize(self, raw_data) -> NewsItem:
        published = raw_data.get("published_parsed")
        publish_date = datetime(*published[:6]) if published else datetime.now()

        # base fields, present in all feeds
        processed_data = {}
        processed_data["title"]        = raw_data.get("title", "")
        processed_data["url"]          = raw_data.get("link", "")
        processed_data["summary"]      = raw_data.get("summary", "")
        processed_data["publish_date"] = publish_date
        processed_data["full_text"]    = str()
        # if new fields are defined, put them inside meta
        processed_data["meta"]         = dict()  

        # call proccessors to fill extra fields in processed data
        for proc in self.processors:
            proc(raw_data, processed_data)

        self.extract_full_text(raw_data, processed_data)
        self.labels_from_tags(raw_data, processed_data)

        # if any of these fields is missing, news item is broken
        required_keys = ["title", "url", "summary", "full_text"]
        if not all([processed_data[key] for key in required_keys]):
            return None

        return NewsItem(**processed_data)
    
    @staticmethod
    def labels_from_tags(raw_data: Dict[str, Any], processed_data: Dict[str, Any]) -> None:
        try:
            tags = raw_data["tags"]
        except KeyError:
            return

        labels = [tag["term"] for tag in tags]

        # if some labels were already present
        if (prev_labels := processed_data["meta"].get("labels")):
            if isinstance(prev_labels, list):
                processed_data["meta"]["labels"].extend(labels)
            else:
                processed_data["meta"]["labels"] = labels + [prev_labels]
        # if no labels were present
        else:
            processed_data["meta"]["labels"] = labels

    @staticmethod    
    def extract_full_text(raw_data: Dict[str, Any], processed_data: Dict[str, Any]) -> None:
        need_text_from_url = True
        text_plain = False
        if (content_list := raw_data.get("content")):

            # if multiple content items, pick the one with plain text
            entry_idx = 0
            for i, content_entry in enumerate(content_list):
                if content_entry.get("type") == "text_plain":
                    text_plain = True
                    entry_idx = i
                    break
            content = content_list[entry_idx]

            if (content_value := content.get("value")):

                # sometimes content value contains only summary, so we 
                # want to fetch text from url despite having it in the feed
                summary = raw_data.get("summary")
                if content_value != summary: 
                    need_text_from_url = False

                if not text_plain:
                    # content_value can still contain no html in which case
                    # trafilatura breaks: prints error logs, returns None
                    prev_disable = logging.root.manager.disable
                    logging.disable(logging.ERROR)
                    full_text = trafilatura.extract(content_value, 
                                                    url=processed_data["url"], # for logs
                                                    fast=False, 
                                                    config=trafilatura_conf)
                    logging.disable(prev_disable)

                if not full_text:
                    full_text = content_value
                processed_data["full_text"] = full_text
                    
        # if no text provided or if text is same as summary, fetch from url
        if (not processed_data["full_text"] or need_text_from_url) and processed_data["url"]:

            # TODO: optionally play w/ User-Agent headers  or requests to bypass 403
            # Also play around with threading since right now this is blocking
            page = trafilatura.fetch_url(processed_data["url"], config=trafilatura_conf)
            if page is not None:
                processed_data["full_text"] = trafilatura.extract(page, 
                                                                  url=processed_data["url"], # for logs
                                                                  fast=False, 
                                                                  config=trafilatura_conf)
                processed_data["meta"]["full_text_from_url"] = True
                
    
    @staticmethod
    def feed_to_json(feed):
        return json.dumps(feed, indent=2, ensure_ascii=False)
