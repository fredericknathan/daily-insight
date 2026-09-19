from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent / "markets.yaml"


@dataclass
class CountryConfig:
    name: str
    index_name: str
    bloomberg: str
    yahoo: str
    currency: str
    fx_ticker: str
    news_query: str
    tv_symbol: str | None
    stock_exchange_suffix: str
    fred_series: str | None
    close_time_local: str
    timezone: str
    verified: bool
    rss_feeds: list[str] = None


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_countries() -> list[CountryConfig]:
    raw = load_config()["countries"]
    return [CountryConfig(**c) for c in raw]
