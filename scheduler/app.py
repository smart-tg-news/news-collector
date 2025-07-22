from datetime import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from crawlers.base import BaseCrawler
from crawlers.rss.crawler_builder import build_rss_crawlers
from crawlers.rss.rss import FetchException
from text_filter.llm_api import TextFilter
from .db import CrawlerDB
from utils.config import load_config


logger = logging.getLogger(__name__)

class CrawlerScheduler:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config: dict = load_config(config_path)
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
                minutes = self.config.get("interval_minutes", 60),
                next_run_time = datetime.now(),
                misfire_grace_time = 60.0,
                name = f"Fetch {crawler.feed_url}"
            )

    @staticmethod
    async def _fetch_job(crawler: BaseCrawler) -> None:
        try:
            news = await crawler.fetch_new()
        except FetchException:
            news = []

        # filter news based on text
        article_filter = TextFilter()
        news_filtered = []
        garbage_count = 0
        for entry in news:
            if await article_filter.check(entry.full_text):
                # news_filtered.append(entry)
                entry.meta['garbage'] = False
            else:
                logger.info(f"Garbage article {entry.url}")
                entry.meta['garbage'] = True
                garbage_count += 1
            news_filtered.append(entry)
        # logger.info(f"{garbage_count} garbage articles out of {len(news)} for {crawler.feed_url}")
        if len(news_filtered) != len(news):
            logger.warning(f"Left {len(news_filtered)} news from {len(news)} for {crawler.feed_url}")
        crawler.save_data(news_filtered)
