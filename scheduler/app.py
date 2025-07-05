import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from crawlers.base import BaseCrawler
from crawlers.rss.crawler_builder import build_rss_crawlers
from utils.config import load_config


logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # send log to console
    ]
)
logger = logging.getLogger(__name__)


async def fetch_job(crawler: BaseCrawler) -> None:
    news = await crawler.fetch_new()
    crawler.save_data(news)


def create_jobs(scheduler: AsyncIOScheduler, config: dict):
    for crawler in build_rss_crawlers(): 
        scheduler.add_job(
            fetch_job, args=[crawler],
            trigger="interval",
            minutes=config.get("interval_minutes", 60),
            next_run_time=datetime.now(),
        )


async def run_scheduler(config_path: str = "config.yaml"):
    config = load_config(config_path)
    scheduler = AsyncIOScheduler()
    create_jobs(scheduler, config)
    scheduler.start()
