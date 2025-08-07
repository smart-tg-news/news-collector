from datetime import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from crawlers.base import BaseCrawler
from crawlers.rss.crawler_builder import build_rss_crawlers
from crawlers.rss.rss import FetchException
from text_filter.llm_api import TextFilter
from .db import CrawlerDB
from utils.config import cfg


logger = logging.getLogger(__name__)

class CrawlerScheduler:
    def __init__(self):
        self.scheduler: AsyncIOScheduler = AsyncIOScheduler()
        self.crawler_db = CrawlerDB()

    async def start(self):
        await self.crawler_db.initialize()
        await self._create_jobs()
        self.scheduler.start()

    async def stop(self):
        self.scheduler.shutdown(wait=True)
        await self.crawler_db.close()

    async def _create_jobs(self):
        for crawler in await build_rss_crawlers(self.crawler_db): 
            self.scheduler.add_job(
                self._fetch_job, args=[crawler],
                trigger = "interval",
                minutes = cfg.interval_minutes,
                next_run_time = datetime.now(),
                misfire_grace_time = 60,
                name = f"Fetch {crawler.feed_url}"
            )

    @staticmethod
    async def _fetch_job(crawler: BaseCrawler) -> None:
        try:
            entries = await crawler.fetch_new()
        except FetchException:
            entries = []

        entries = crawler.normalize_entries(entries)

        # filter news based on text
        llm_filter = TextFilter()
        garbage_count = 0
        for entry in entries:

            is_garbage = False
            try:
                is_garbage = not await llm_filter.check(entry.full_text)
            except Exception as e:
                logger.warning(f"LLM check failed with exception: {repr(e)} for article {entry.url}")
                is_garbage = False

            if is_garbage:
                logger.info(f"Garbage article {entry.url}")
                garbage_count += 1

            entry.meta['garbage'] = is_garbage

        if garbage_count:
            logger.info(f"{garbage_count} garbage articles out of {len(entries)} for {crawler.feed_url}")

        crawler.save_data(entries)
