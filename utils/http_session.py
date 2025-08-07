from functools import lru_cache
import aiohttp


""" Single ClientSession for all crawlers and requests """
@lru_cache(maxsize=1)
def get_shared_session() -> aiohttp.ClientSession:
    connector = aiohttp.TCPConnector(limit_per_host=200)
    timeout   = aiohttp.ClientTimeout(total=60)
    return aiohttp.ClientSession(connector=connector, timeout=timeout)

async def close_shared_session() -> None:
    sess = get_shared_session()
    await sess.close()
    get_shared_session.cache_clear()