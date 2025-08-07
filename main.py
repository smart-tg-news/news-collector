import asyncio
from dotenv import load_dotenv
import logging
import sys
from pathlib import Path

from utils import config
from utils.log import setup_logging
    

if __name__ == "__main__":
    # configure global log settings and get logger
    log_dir = Path(__file__).resolve().parent / "log"
    setup_logging(log_dir)
    logger = logging.getLogger(__name__)

    # load global config
    config.init_config(yaml_path="config/config.yaml", args=sys.argv[1:])

    from utils.config import cfg
    logger.info(f"Running with debug={cfg.debug}")
    if cfg.clean_crawler_db:
        logger.info(f"Crawler db {cfg.crawler_db} will be cleaned")

    # load global env
    load_dotenv()

    # local imports after setting the environment
    from scheduler.app import CrawlerScheduler
    from db.client import MongoClientSingleton

    # init DB
    MongoClientSingleton.init()
    # instantiate scheduler
    crawler_scheduler = CrawlerScheduler()

    # create a fresh event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # asyncio loop config
    loop.set_debug(True)
    # warn if any callback (including job dispatch) takes >100 ms
    loop.slow_callback_duration = 30.0  

    try:
        # schedule the “start” coroutine and run forever
        loop.create_task(crawler_scheduler.start())
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received")
    finally:
        # synchronously wait for the async stop() to finish
        loop.run_until_complete(crawler_scheduler.stop())
        logger.info("Scheduler stopped")

        from utils.http_session import close_shared_session
        loop.run_until_complete(close_shared_session())

        # close db connection
        MongoClientSingleton.close()

        # loop cleanup
        loop.close()
