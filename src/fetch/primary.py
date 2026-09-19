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
    news_headlines: list[str]
    source: str = "yfinance_rss"
    stale: bool = False


def _fetch_news(query: str) -> list[str]:
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}+when:1d&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)
        return [entry.title for entry in feed.entries]
    except Exception as e:
        logger.warning(f"Failed to fetch news for query '{query}': {e}")
        return []

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
                    last_close = round(float(df["Close"].iloc[-1]), 2)
                    change_pct = round(t_info.get("regularMarketChangePercent", 0.0), 2)
                    if change_pct == 0.0 and "previousClose" in t_info:
                         change_pct = round((last_close - t_info["previousClose"]) / t_info["previousClose"] * 100, 2)
                    out[country] = {"price": last_close, "change_pct": change_pct, "ytd_pct": None}
                    continue
                else:
                    out[country] = None
                    continue
            last_close = round(float(df["Close"].iloc[-1]), 2)
            prev_close = float(df["Close"].iloc[-2])
            change_pct = round((last_close - prev_close) / prev_close * 100, 2)

            jan1_idx = df.index[df.index.year == df.index[-1].year][0]
            jan1_close = float(df.loc[jan1_idx, "Close"])
            ytd_pct = round((last_close - jan1_close) / jan1_close * 100, 2)

            out[country] = {"price": last_close, "change_pct": change_pct, "ytd_pct": ytd_pct}
        except Exception as e:
            logger.warning("Could not parse yfinance data for %s (%s): %s", country, symbol, e)
            out[country] = None
    return out

def fetch_all(markets: list[dict]) -> dict[str, Optional[MarketSnapshot]]:
    results = {}
    valid_markets = [m for m in markets if m.get("yahoo")]
    
    tickers = {m["name"]: m["yahoo"] for m in valid_markets}
    prices = _yfinance_batch(tickers)

    for m in valid_markets:
        name = m["name"]
        price_data = prices.get(name)
        if not price_data:
            results[name] = None
            continue

        news_query = m.get("news_query", f"{name} stock market")
        headlines = _fetch_news(news_query)

        results[name] = MarketSnapshot(
            country=name,
            ticker=m["yahoo"],
            price=price_data["price"],
            change_pct=price_data["change_pct"],
            ytd_pct=price_data["ytd_pct"],
            news_headlines=headlines,
        )
    return results
