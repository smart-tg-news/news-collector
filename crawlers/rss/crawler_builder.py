from .rss import RSSCrawler
from .extra_field_processors import (
    full_text_from_content
)
from .filter import (
    IdFilterStrategy
)


def build_ycombinator_crawler(db, feed_url="https://news.ycombinator.com/rss"):
    return RSSCrawler(
        feed_url=feed_url
    )

def build_verge_crawler(db, feed_url="https://www.theverge.com/rss/index.xml"):
    return RSSCrawler(
        feed_url=feed_url, 
        processors=[full_text_from_content], 
        filter_strategy=IdFilterStrategy(db)
    )

def build_techcrunch_feed(db, feed_url="https://techcrunch.com/feed/"):
    return RSSCrawler(
        feed_url=feed_url, 
        filter_strategy=IdFilterStrategy(db)
    )

"""Got 403 error"""
# def build_lifehacker_feed(db, feed_url="https://lifehacker.com/feed/rss"):
#     return RSSCrawler(
#         feed_url=feed_url, 
#         # filter_strategy=IdFilterStrategy(db)
#     )

"https://www.wired.com/feed/tag/ai/latest/rss"


"""Different feed for different labels; summary field is called 'description'"""
def build_wired_ai_feed(db, feed_url="https://www.wired.com/feed/tag/ai/latest/rss"):
    return RSSCrawler(
        feed_url=feed_url, 
        # filter_strategy=IdFilterStrategy(db)
    )

def build_rss_crawlers(crawler_db):
    crawlers = []
    # crawlers.append(build_ycombinator_crawler(crawler_db))
    # crawlers.append(build_verge_crawler(crawler_db))
    # crawlers.append(build_techcrunch_feed(crawler_db))
    crawlers.append(build_wired_ai_feed(crawler_db))

    return crawlers
