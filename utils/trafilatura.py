from copy import deepcopy
from functools import lru_cache


@lru_cache(maxsize=1)
def get_trafilatura_config() -> dict:
    from trafilatura.settings import DEFAULT_CONFIG

    new_config = deepcopy(DEFAULT_CONFIG)
    new_config['DEFAULT']['DOWNLOAD_TIMEOUT'] = '3'

    return new_config