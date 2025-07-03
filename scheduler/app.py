import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from crawlers.rss import RSSCrawler
from utils.config import load_config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_jobs(scheduler: AsyncIOScheduler, config: dict):
    for feed in config.get("rss_feeds", []):
        crawler = RSSCrawler(feed_url=feed)
        scheduler.add_job(
            lambda c=crawler: asyncio.create_task(c.fetch_new()),
            "interval",
            minutes=config.get("interval_minutes", 60),
            next_run_time=datetime.utcnow(),
        )


def run(config_path: str = "config.yaml"):
    config = load_config(config_path)
    scheduler = AsyncIOScheduler()
    create_jobs(scheduler, config)
    scheduler.start()
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    run()
