from .rss import RSSCrawler
from .extra_field_processors import (
    full_text_from_content
)


def build_verge_crawler(feed_url="https://www.theverge.com/rss/index.xml"):
    return RSSCrawler(
        feed_url=feed_url, 
        feed_procs=[full_text_from_content]
    )

def build_rss_crawlers():
    crawlers = []
    crawlers.append(build_verge_crawler())
    return crawlers