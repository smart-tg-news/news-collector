from abc import ABC, abstractmethod
from typing import List
import feedparser
from datetime import datetime
import logging

from scheduler.db import CrawlerDB 


logger = logging.getLogger(__name__)

class FilterStrategy(ABC):
    @abstractmethod
    async def filter_new(
        self,
        feed: feedparser.FeedParserDict,
        feed_id: str
    ) -> List[dict]:
        """Return feed entries that are “new” since last run."""


class IdFilterStrategy(FilterStrategy):
    def __init__(self, db: CrawlerDB):
        self.db = db

    async def filter_new(self, feed, feed_id):
        current_ids = [
            e.get("id") or e.get("guid") or e.get("link")
            for e in feed.entries
        ]
        prev_ids = await self.db.get_seen_ids(feed_id)
        new_ids = set(current_ids) - set(prev_ids)

        # store the full batch for next time
        await self.db.replace_seen_ids(feed_id, current_ids)

        return [e for e in feed.entries
                if (e.get("id") or e.get("guid") or e.link) in new_ids]
    

class PublishDateFilterStrategy(FilterStrategy):
    def __init__(self, db: CrawlerDB):
        self.db = db

    async def filter_new(self, feed, feed_id):

        # check if 'published_parsed' field is present
        if not feed.entries[0].get("published_parsed"):
            logging.warning(f'Field "published_parsed" not found in feed {feed_id}. '
                             'No entries will be filtered based on publish date')
            return feed.entries
        
        # find entries with publish dates greater than the last saved date
        current_dates = [datetime(*entry.published_parsed[:6]) 
                         for entry in feed.entries]
        latest_date = await self.db.get_latest_date(feed_id)
        new_entries = [
            e for e, dt in zip(feed.entries, current_dates) if dt > latest_date]
        
        # replace latest date in the db
        if new_entries:
            await self.db.set_latest_date(feed_id, max(current_dates))

        return new_entries
