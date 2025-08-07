import yaml
from functools import partial
from typing import List, Dict, Any
import logging

from text_filter.llm_api import TextFilter
from utils.config import cfg
from .filter import IdFilterStrategy, PublishDateFilterStrategy
from .extra_field_processors import (
    full_text_from_content,
    labels_from_tags,
    set_explicit_label,
    FieldProcessorException,
)
from .rss import RSSCrawler, FetchException


logger = logging.getLogger(__name__)


# Path to YAML config for RSS feeds
FEEDS_CONFIG_PATH = cfg.feeds_config_path

# Registry mapping names in YAML to actual processor callables
PROCESSOR_REGISTRY: Dict[str, Any] = {
    'full_text_from_content': lambda x, y: ...,
    'labels_from_tags': lambda x, y: ...,
    'set_explicit_label': set_explicit_label,  # requires partial
}

# Registry mapping names in YAML to filter strategy classes
FILTER_STRATEGY_REGISTRY = {
    'IdFilterStrategy': IdFilterStrategy,
    'PublishDateFilterStrategy': PublishDateFilterStrategy,
    # 'None': NoFilterStrategy,
}

async def build_rss_crawlers(db) -> List[RSSCrawler]:
    """
    Load crawler definitions from YAML, auto-detect best processors,
    update config when necessary, and return instantiated crawlers.
    """
    logger.info("Start building crawlers")

    # Load existing YAML config
    with open(FEEDS_CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    crawlers: List[RSSCrawler] = []
    update_config = False

    for feed in config.get('feeds', []):
        try:
            feed_url = feed['feed_url']
            fixed    = feed.get('fixed', False)
            broken   = feed.get('broken', False)

            if broken:
                continue

            # Instantiate filter strategy
            strat_name = feed.get('filter_strategy', 'IdFilterStrategy')
            StratCls = FILTER_STRATEGY_REGISTRY.get(strat_name, IdFilterStrategy)
            filter_strategy = StratCls(db)

            # Parse any user-specified processors
            processors = []
            for proc_cfg in feed.get('processors', []):
                if isinstance(proc_cfg, str):
                    processors.append(PROCESSOR_REGISTRY[proc_cfg])
                elif isinstance(proc_cfg, dict):
                    name, param = next(iter(proc_cfg.items()))
                    fn = PROCESSOR_REGISTRY[name]
                    # Wrap with partial to bind label parameter
                    processors.append(partial(fn, label=param))

            if not fixed:

                # check if we can fetch the feed successfully
                crawler = RSSCrawler(feed_url=feed_url)
                try:
                    entries = await crawler.fetch_new(dry_run=True)
                    if not entries:
                        logger.warning(f"Got no entries from feed {crawler.feed_url}")
                        broken = True
                except FetchException:
                    logger.warning(f"Feed {feed_url} broken")
                    broken = True

                if not broken:
                    # check if we can normalise enough values
                    normalised_entries = crawler.normalize_entries(entries)
                    if len(normalised_entries) < len(entries) // 2:
                        logger.warning(f"Wasn't able to normalize enough entries from {crawler.feed_url}")
                        broken = True

                    # check if articles are not garbage
                    llm_filter = TextFilter()
                    garbage_cnt = 0

                    for entry in normalised_entries:
                        is_garbage = True
                        try:
                            is_garbage = not await llm_filter.check(entry.full_text)
                        except Exception:
                            is_garbage = False

                        if is_garbage:
                            garbage_cnt += 1

                    if garbage_cnt > len(normalised_entries) // 2:
                        logger.warning(f"Too many garbage articles ({garbage_cnt} of {len(normalised_entries)})" 
                                    f"in feed {crawler.feed_url}")
                        broken = True   

                if broken:
                    feed['broken'] = True

                feed['fixed'] = True
                update_config = True

            # Instantiate the final crawler
            if not broken:
                crawlers.append(
                    RSSCrawler(
                        feed_url=feed_url,
                        filter_strategy=filter_strategy,
                        processors=processors,
                    )
                )

        except:
            if update_config:
                with open(FEEDS_CONFIG_PATH, 'w') as f:
                    yaml.safe_dump(config, f)
            raise

    # If any new configs were fixed, write back to YAML
    if update_config:
        with open(FEEDS_CONFIG_PATH, 'w') as f:
            yaml.safe_dump(config, f)

    logger.info(f"Successfully built {len(crawlers)} crawlers")

    return crawlers
