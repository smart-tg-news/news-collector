from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from crawlers.base import BaseCrawler
from crawlers.rss.crawler_builder import build_rss_crawlers
from .db import CrawlerDB
from utils.config import load_config



class CrawlerScheduler:
    def __init__(self, config_path: str = "config.yaml"):
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
                trigger="interval",
                minutes=self.config.get("interval_minutes", 60),
                next_run_time=datetime.now(),
                name=f"Fetch {crawler.feed_url}"
            )

    @staticmethod
    async def _fetch_job(crawler: BaseCrawler) -> None:
        news = await crawler.fetch_new()
        crawler.save_data(news)
