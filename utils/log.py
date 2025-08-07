import logging
from logging.handlers import TimedRotatingFileHandler
import os


def setup_logging(log_dir):
    # ensure log dir exists
    os.makedirs(log_dir, exist_ok=True)

    # logs to file
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        when="midnight",     # roll over at midnight
        interval=1,          # every day
        backupCount=7,       # keep 7 days of logs
        encoding="utf-8",
    )
    # rename rotated files to app.log.YYYY-MM-DD
    file_handler.suffix = "%Y-%m-%d"

    # logs to console
    console_handler = logging.StreamHandler()

    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[console_handler, file_handler]
    )
