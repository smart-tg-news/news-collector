import asyncio
from dotenv import load_dotenv
import logging
import sys

from utils import config
    

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # send log to console
    ]
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # load global config
    config.init_config(yaml_path="config/config.yaml", args=sys.argv[1:])

    from utils.config import cfg
    logging.info(f"Running with debug={cfg.debug}")
    if cfg.clean_crawler_db:
        logging.info(f"Crawler db {cfg.crawler_db} will be cleaned")

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
        logging.info("Shutdown signal received")
    finally:
        # synchronously wait for the async stop() to finish
        loop.run_until_complete(crawler_scheduler.stop())
        logging.info("Scheduler stopped")

        from utils.http_session import close_shared_session
        loop.run_until_complete(close_shared_session())

        # close db connection
        MongoClientSingleton.close()

        # loop cleanup
        loop.close()
