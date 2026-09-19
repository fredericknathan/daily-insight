from __future__ import annotations
import logging
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import yfinance as yf
import feedparser

logger = logging.getLogger(__name__)

@dataclass
class MarketSnapshot:
    country: str
    ticker: str
    price: Optional[float]
    change_pct: Optional[float]
    ytd_pct: Optional[float]
    fx_price: Optional[float] = None
    fx_change_pct: Optional[float] = None
    news_headlines: list[str] = None
    source: str = "yfinance_rss"
    stale: bool = False

def _is_fresh(entry, max_age_hours: int = 36) -> bool:
    """Return True if the RSS entry is within max_age_hours old."""
    import time
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        pub_time = time.mktime(entry.published_parsed)
        return (time.time() - pub_time) <= max_age_hours * 3600
    return True  # no date → accept it


_FINANCE_KEYWORDS = {
    'stock', 'share', 'market', 'index', 'rally', 'sell', 'buy', 'trade', 'trading',
    'invest', 'fund', 'equity', 'bond', 'yield', 'rate', 'bank', 'central bank',
    'inflation', 'gdp', 'economy', 'economic', 'finance', 'financial', 'currency',
    'forex', 'exchange', 'profit', 'earnings', 'revenue', 'ipo', 'merger', 'acquisition',
    'dividend', 'quarter', 'fiscal', 'monetary', 'policy', 'growth', 'recession',
    'export', 'import', 'trade', 'deficit', 'surplus', 'debt', 'credit', 'loan',
    'interest', 'fed', 'boj', 'ecb', 'bsp', 'mas', 'ojk', 'sbv', 'boa',
    'nikkei', 'kospi', 'hang seng', 'vn-index', 'psei', 'jci', 'sti', 's&p',
    'nasdaq', 'dow', 'sensex', 'yen', 'won', 'dong', 'peso', 'rupiah', 'ringgit',
}

def _is_financial(headline: str) -> bool:
    """Return True if the headline is plausibly financial/market-related."""
    lower = headline.lower()
    return any(kw in lower for kw in _FINANCE_KEYWORDS)


def _fetch_rss(url: str, require_financial: bool = True) -> list[str]:
    """Fetch headlines from a single RSS feed URL, enforcing 36h freshness."""
    try:
        feed = feedparser.parse(url)
        results = []
        for e in feed.entries:
            if not _is_fresh(e):
                continue
            if require_financial and not _is_financial(e.title):
                continue
            results.append(e.title)
        return results
    except Exception as e:
        logger.warning("RSS fetch failed for %s: %s", url, e)
        return []


def _fetch_news(query: str, extra_rss: list[str] | None = None) -> list[str]:
    """Fetch headlines from Google News + any country-specific RSS feeds."""
    all_headlines: list[str] = []
    seen: set[str] = set()

    # 1. Country-specific publication RSS feeds (highest quality / most targeted)
    for rss_url in (extra_rss or []):
        for h in _fetch_rss(rss_url):
            key = h.lower().strip()
            if key not in seen:
                seen.add(key)
                all_headlines.append(h)

    # 2. Google News RSS (broad aggregator — fills gaps)
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}+when:1d&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if _is_fresh(entry):
                key = entry.title.lower().strip()
                if key not in seen:
                    seen.add(key)
                    all_headlines.append(entry.title)
    except Exception as e:
        logger.warning("Google News fetch failed for query '%s': %s", query, e)

    logger.info("Fetched %d unique headlines for query '%s'", len(all_headlines), query)
    return all_headlines

def _yfinance_batch(tickers: dict[str, str]) -> dict[str, Optional[dict]]:
    symbols = list(tickers.values())
    try:
        data = yf.download(
            symbols, period="1y", group_by="ticker",
            progress=False, threads=True,
        )
    except Exception as e:
        logger.error("yfinance batch call failed entirely: %s", e)
        return {country: None for country in tickers}

    out = {}
    for country, symbol in tickers.items():
        try:
            df = data[symbol] if len(symbols) > 1 else data
            df = df.dropna()
            if len(df) < 2:
                if len(df) == 1:
                    t_info = yf.Ticker(symbol).info
                    last_close = round(float(df["Close"].iloc[-1]), 4)
                    change_pct = round(t_info.get("regularMarketChangePercent", 0.0), 2)
                    if change_pct == 0.0 and "previousClose" in t_info:
                         change_pct = round((last_close - t_info["previousClose"]) / t_info["previousClose"] * 100, 2)
                    out[country] = {"price": last_close, "change_pct": change_pct, "ytd_pct": None}
                    continue
                else:
                    out[country] = None
                    continue
            last_close = round(float(df["Close"].iloc[-1]), 4)
            prev_close = float(df["Close"].iloc[-2])
            change_pct = round((last_close - prev_close) / prev_close * 100, 2)

            try:
                jan1_idx = df.index[df.index.year == df.index[-1].year][0]
                jan1_close = float(df.loc[jan1_idx, "Close"])
                ytd_pct = round((last_close - jan1_close) / jan1_close * 100, 2)
            except Exception:
                ytd_pct = None

            out[country] = {"price": last_close, "change_pct": change_pct, "ytd_pct": ytd_pct}
        except Exception as e:
            logger.warning("Could not parse yfinance data for %s (%s): %s", country, symbol, e)
            out[country] = None
    return out

def fetch_all(markets: list[dict]) -> dict[str, Optional[MarketSnapshot]]:
    results = {}
    valid_markets = [m for m in markets if m.get("yahoo")]
    
    tickers = {m["name"]: m["yahoo"] for m in valid_markets}
    fx_tickers = {m["name"]: m["fx_ticker"] for m in valid_markets if m.get("fx_ticker")}
    
    prices = _yfinance_batch(tickers)
    fx_prices = _yfinance_batch(fx_tickers)

    for m in valid_markets:
        name = m["name"]
        price_data = prices.get(name)
        fx_data = fx_prices.get(name)
        
        if not price_data:
            results[name] = None
            continue

        news_query = m.get("news_query", f"{name} stock market")
        extra_rss = m.get("rss_feeds", [])
        headlines = _fetch_news(news_query, extra_rss=extra_rss)

        results[name] = MarketSnapshot(
            country=name,
            ticker=m["yahoo"],
            price=price_data["price"],
            change_pct=price_data["change_pct"],
            ytd_pct=price_data["ytd_pct"],
            fx_price=fx_data["price"] if fx_data else None,
            fx_change_pct=fx_data["change_pct"] if fx_data else None,
            news_headlines=headlines,
        )
    return results
