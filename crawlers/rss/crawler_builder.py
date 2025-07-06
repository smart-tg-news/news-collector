from functools import partial

from .rss import RSSCrawler
from .extra_field_processors import (
    full_text_from_content, 
    labels_from_tags, 
    set_explicit_label
)
from .filter import (
    IdFilterStrategy, 
    PublishDateFilterStrategy
)


def build_ycombinator_crawler(db, feed_url="https://news.ycombinator.com/rss"):
    return RSSCrawler(
        feed_url=feed_url, 
        filter_strategy=PublishDateFilterStrategy(db)
    )

def build_verge_crawler(db, feed_url="https://www.theverge.com/rss/index.xml"):
    return RSSCrawler(
        feed_url=feed_url, 
        processors=[full_text_from_content, labels_from_tags], 
        filter_strategy=IdFilterStrategy(db)
    )

def build_techcrunch_feed(db, feed_url="https://techcrunch.com/feed/"):
    return RSSCrawler(
        feed_url=feed_url, 
        processors=[labels_from_tags],
        filter_strategy=IdFilterStrategy(db)
    )

"""Got 403 error"""
# def build_lifehacker_feed(db, feed_url="https://lifehacker.com/feed/rss"):
#     return RSSCrawler(
#         feed_url=feed_url, 
#         # filter_strategy=IdFilterStrategy(db)
#     )



def build_wired_feed(db):
    """
    Apart from category taxonomy there is also distinction by tags, e.g.
    "https://www.wired.com/feed/tag/ai/latest/rss"
    "https://www.wired.com/feed/tag/wired-guide/latest/rss"

    But presumably tags are included in categories, yet this is still 
    to be confirmed
    """

    feed_tmpl = "https://www.wired.com/feed/category/{category}/latest/rss".format

    crawlers = []
    for label in ['business', 'culture', 'gear', 'ideas', 
                  'science', 'security', 'backchannel']:
        
        label_processor = partial(set_explicit_label, label=label)
        crawler = RSSCrawler(
            feed_url=feed_tmpl(category=label), 
            processors=[label_processor, labels_from_tags],
            filter_strategy=IdFilterStrategy(db)
        )
        crawlers.append(crawler)    

    return crawlers



def build_rss_crawlers(crawler_db):
    crawlers = []
    crawlers.append(build_ycombinator_crawler(crawler_db))
    crawlers.append(build_verge_crawler(crawler_db))
    crawlers.append(build_techcrunch_feed(crawler_db))
    crawlers.extend(build_wired_feed(crawler_db))

    return crawlers
