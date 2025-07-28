import yaml
import argparse
from dataclasses import dataclass, field, fields

@dataclass
class Config:
    interval_minutes: int       = field(default=60)
    feeds_config_path: str      = field(default="config/rss_feeds.yml")
    crawler_db: str             = field(default="feeds.db")
    filter_llm: str             = field(default="mistralai/mistral-small-3.2-24b-instruct:free")

    mongo_db: str               = field(default="Test")
    mongo_table: str            = field(default="news")

    debug: bool                 = field(default=False)
    clean_crawler_db: bool      = field(default=False)

# this variable is global config
cfg: Config

def init_config(
    yaml_path: str = "config.yaml",
    args=None,               # for testing, you can pass in a list of strings
) -> None:
    global cfg

    # 1) Load defaults + YAML
    with open(yaml_path) as f:
        raw = yaml.safe_load(f) or {}
    c = Config()  # defaults
    for key, val in raw.items():
        if hasattr(c, key):
            setattr(c, key, val)

    # 2) Build CLI only for the fields you want exposed
    parser = argparse.ArgumentParser()
    cli_fields = {"debug", "clean_crawler_db"}  # pick your CLI vs YAML‑only keys
    for f in fields(Config):
        if f.name in cli_fields:
            flag = f"--{f.name.replace('_','-')}"
            if f.type is bool:
                parser.add_argument(flag, dest=f.name, action="store_true")
            else:
                parser.add_argument(flag, type=f.type)

    parsed = parser.parse_args(args)

    # 3) Override from CLI
    for key, val in vars(parsed).items():
        if val is not None:
            setattr(c, key, val)

    cfg = c

