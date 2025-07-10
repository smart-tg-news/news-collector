import yaml
from functools import partial
from typing import List, Dict, Any

from .filter import IdFilterStrategy, PublishDateFilterStrategy
from .extra_field_processors import (
    full_text_from_content,
    labels_from_tags,
    set_explicit_label,
    FieldProcessorException,
)
from .rss import RSSCrawler


# Path to YAML config for RSS feeds
CONFIG_PATH = 'config/rss_feeds.yml'

# Registry mapping names in YAML to actual processor callables
PROCESSOR_REGISTRY: Dict[str, Any] = {
    'full_text_from_content': full_text_from_content,
    'labels_from_tags': labels_from_tags,
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
    # Load existing YAML config
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    crawlers: List[RSSCrawler] = []
    updated = False

    for entry in config.get('feeds', []):
        feed_url = entry['feed_url']
        fixed    = entry.get('fixed', False)

        # Instantiate filter strategy
        strat_name = entry.get('filter_strategy', 'IdFilterStrategy')
        StratCls = FILTER_STRATEGY_REGISTRY.get(strat_name, IdFilterStrategy)
        filter_strategy = StratCls(db)

        # Parse any user-specified processors
        configured_processors = []
        for proc_cfg in entry.get('processors', []):
            if isinstance(proc_cfg, str):
                configured_processors.append(PROCESSOR_REGISTRY[proc_cfg])
            elif isinstance(proc_cfg, dict):
                name, param = next(iter(proc_cfg.items()))
                fn = PROCESSOR_REGISTRY[name]
                # Wrap with partial to bind label parameter
                configured_processors.append(partial(fn, label=param))

        if fixed:
            processors = configured_processors
        else:
            # Auto-detect vs testable processors
            testable = [full_text_from_content, labels_from_tags]
            good = []
            for proc in testable:
                try:
                    crawler = RSSCrawler(
                        feed_url=feed_url,
                        filter_strategy=None,
                        processors=[proc],
                    )
                    # if this throws FieldProcessorException, it means proc isn't supported
                    await crawler.fetch_new()
                except FieldProcessorException:
                    continue
                else:
                    good.append(proc)

            # TODO: FUUUUUCK sometimes different feed entries can have or not have tags.
            # This means that we wont apply tag processor yet many entries require that.
            # Apparently we should use the tag processor for such feed to without
            # raising if no tag found. Same problem might occur with other processors i guess

            # Filter out duplicates from configured processors
            unique_configured = [p for p in configured_processors if p not in good]
            # Combine auto-detected + explicitly configured
            processors = good + unique_configured

            # Update YAML config
            entry['processors'] = []
            for p in processors:
                if hasattr(p, 'func') and p.func is set_explicit_label:
                    # Extract the bound 'label' argument
                    label_val = p.keywords.get('label')
                    entry['processors'].append({ 'set_explicit_label': label_val })
                else:
                    # Find by value in registry
                    for name, fn in PROCESSOR_REGISTRY.items():
                        if fn is p:
                            entry['processors'].append(name)
                            break
            entry['fixed'] = True
            updated = True

        # Instantiate the final crawler
        crawlers.append(
            RSSCrawler(
                feed_url=feed_url,
                filter_strategy=filter_strategy,
                processors=processors,
            )
        )

    # If any new configs were fixed, write back to YAML
    if updated:
        with open(CONFIG_PATH, 'w') as f:
            yaml.safe_dump(config, f)

    return crawlers
