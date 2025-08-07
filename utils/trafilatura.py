from copy import deepcopy
from functools import lru_cache
import logging
from contextlib import contextmanager


@lru_cache(maxsize=1)
def get_trafilatura_config() -> dict:
    from trafilatura.settings import DEFAULT_CONFIG

    new_config = deepcopy(DEFAULT_CONFIG)
    new_config['DEFAULT']['DOWNLOAD_TIMEOUT'] = '3'

    return new_config


@contextmanager
def suppress_trafilatura_logs(level=logging.ERROR):
    """
    Suppress all trafilatura logs at or below `level`.
    By default, level=ERROR will drop warnings & errors but let CRITICAL pass.
    """
    # Remember the root disable state
    prev_disable = logging.root.manager.disable
    # Turn on global suppression up to the requested level
    logging.disable(level)
    try:
        yield
    finally:
        # Restore global suppression to whatever it was before
        logging.disable(prev_disable)
