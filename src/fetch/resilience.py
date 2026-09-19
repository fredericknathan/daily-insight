"""
The resilience chain described in the outline, updated:

    primary (yfinance + RSS) --fails-->  last committed good value (data/*.json)

This is the one file that decides, per country, which source actually
won today and stamps that decision onto the output so the email/log can
show it. Nothing here should ever crash the whole run because one
country's data is missing — worst case, that country is labelled STALE
or UNAVAILABLE and the rest of the brief still sends.
"""

from __future__ import annotations
import glob
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

from src.fetch.primary import MarketSnapshot

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


@dataclass
class ResolvedSnapshot:
    country: str
    price: Optional[float]
    change_pct: Optional[float]
    ytd_pct: Optional[float]
    news_headlines: list
    source: str          # "yfinance_rss" | "cache" | "unavailable"
    stale: bool
    as_of: str


def _load_last_good(country: str) -> Optional[dict]:
    """Walk data/*.json newest-first, return the most recent entry for
    this country that has a real price in it."""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")), reverse=True)
    for path in files:
        try:
            with open(path) as f:
                day = json.load(f)
            for entry in day.get("countries", []):
                if entry["name"] == country and entry.get("close") is not None:
                    return {
                        "price": entry["close"],
                        "change_pct": entry.get("change_pct"),
                        "ytd_pct": entry.get("ytd_pct"),
                        "as_of": day.get("date", "unknown"),
                    }
        except Exception:
            continue
    return None


def resolve_all(
    markets: list[dict],
    primary_results: dict[str, Optional[MarketSnapshot]],
) -> list[ResolvedSnapshot]:
    today = datetime.now().strftime("%Y-%m-%d")
    resolved = []

    for m in markets:
        name = m["name"]
        snap = primary_results.get(name)

        if snap is not None:
            resolved.append(ResolvedSnapshot(
                country=name, price=snap.price, change_pct=snap.change_pct,
                ytd_pct=snap.ytd_pct, news_headlines=snap.news_headlines,
                source="yfinance_rss", stale=False, as_of=today,
            ))
            continue

        cached = _load_last_good(name)
        if cached is not None:
            logger.warning("%s: falling back to cached value from %s", name, cached["as_of"])
            resolved.append(ResolvedSnapshot(
                country=name, price=cached["price"], change_pct=cached["change_pct"],
                ytd_pct=cached["ytd_pct"], news_headlines=[],
                source="cache", stale=True, as_of=cached["as_of"],
            ))
            continue

        logger.error("%s: no data from any source — will show as unavailable", name)
        resolved.append(ResolvedSnapshot(
            country=name, price=None, change_pct=None, ytd_pct=None,
            news_headlines=[], source="unavailable", stale=True, as_of=today,
        ))

    return resolved


def write_daily_snapshot(resolved: list[ResolvedSnapshot], rates: dict[str, Optional[float]]):
    """Commits today's resolved data to data/YYYY-MM-DD.json — this file
    IS the archive AND the cache fallback for tomorrow."""
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{today}.json")

    payload = {
        "date": today,
        "generated_at": datetime.now().isoformat(),
        "countries": [
            {
                "name": r.country,
                "close": r.price,
                "change_pct": r.change_pct,
                "ytd_pct": r.ytd_pct,
                "rate_10y_pct": rates.get(r.country),
                "source": r.source,
                "stale": r.stale,
                "news_headlines": r.news_headlines,
            }
            for r in resolved
        ],
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info("Wrote snapshot to %s", path)
    return path
