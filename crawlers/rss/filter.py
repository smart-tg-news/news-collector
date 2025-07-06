from abc import ABC, abstractmethod
from typing import List
import feedparser

from scheduler.db import CrawlerDB 


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
