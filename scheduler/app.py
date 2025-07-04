import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from crawlers.rss import RSSCrawler
from crawlers.base import BaseCrawler
from utils.config import load_config


logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # send log to console
    ]
)
logger = logging.getLogger(__name__)


async def job(crawler: BaseCrawler) -> None:
    news = await crawler.fetch_new()
    crawler.save_data(news)


def create_jobs(scheduler: AsyncIOScheduler, config: dict):
    logger.info("Inside create_jobs")
    for feed in config.get("rss_feeds", []):
        crawler = RSSCrawler(feed_url=feed)
        scheduler.add_job(
            job, args=[crawler],
            trigger="interval",
            minutes=config.get("interval_minutes", 60),
            next_run_time=datetime.now(),
        )


async def run_scheduler(config_path: str = "config.yaml"):
    config = load_config(config_path)
    scheduler = AsyncIOScheduler()
    create_jobs(scheduler, config)
    scheduler.start()
