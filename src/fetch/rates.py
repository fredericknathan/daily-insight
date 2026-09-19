"""
10Y sovereign yield for all markets.
FRED is used for USA, Japan, Korea (if FRED_API_KEY is provided).
TradingView is scraped via Playwright for the rest (HK, ID, SG, PH, VN).
"""

from __future__ import annotations
import logging
import os
from typing import Optional

import requests
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

FRED_API_BASE = "https://api.stlouisfed.org/fred/series/observations"
FRED_API_KEY = os.environ.get("FRED_API_KEY")


def fetch_fred_yield(series_id: str) -> Optional[dict]:
    if not FRED_API_KEY:
        logger.warning("FRED_API_KEY not set — skipping FRED fetch")
        return None
    if not series_id:
        return None
    try:
        resp = requests.get(
            FRED_API_BASE,
            params={
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 2,
            },
            timeout=10,
        )
        resp.raise_for_status()
        obs = resp.json().get("observations", [])
        if not obs or obs[0]["value"] == ".":
            return None
        
        curr = float(obs[0]["value"])
        bps = None
        if len(obs) == 2 and obs[1]["value"] != ".":
            prev = float(obs[1]["value"])
            bps = round((curr - prev) * 100, 1)
            
        return {"rate": round(curr, 3), "bps_change": bps}
    except Exception as e:
        logger.warning("FRED fetch failed for series %s: %s", series_id, e)
        return None


def fetch_tv_yields(tv_symbols: dict[str, str]) -> dict[str, dict]:
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Create a single context to speed up page loads
        context = browser.new_context()
        
        for country, symbol in tv_symbols.items():
            page = context.new_page()
            try:
                url = f"https://www.tradingview.com/symbols/{symbol}/"
                page.goto(url, wait_until="networkidle", timeout=15000)
                
                # Wait for JS to populate the price
                try:
                    page.wait_for_function("document.querySelector('.js-symbol-last') && document.querySelector('.js-symbol-last').innerText.trim() !== ''", timeout=5000)
                except Exception:
                    pass  # if it times out, we just try to evaluate anyway
                
                price_str = page.evaluate("document.querySelector('.js-symbol-last') ? document.querySelector('.js-symbol-last').innerText : ''")
                change_str = page.evaluate("document.querySelector('.js-symbol-change-pt') ? document.querySelector('.js-symbol-change-pt').innerText : ''")
                
                if price_str:
                    rate = round(float(price_str.replace(',', '')), 3)
                    bps = None
                    if change_str:
                        # TV displays unicode minus \u2212, replace with standard hyphen
                        clean_change = change_str.replace('\u2212', '-').strip()
                        try:
                            bps = round(float(clean_change) * 100, 1)
                        except Exception:
                            pass
                    results[country] = {"rate": rate, "bps_change": bps}
                else:
                    results[country] = None
                    logger.warning(f"Could not find TV price for {country} ({symbol})")
            except Exception as e:
                logger.warning(f"TradingView fetch failed for {country} ({symbol}): {e}")
                results[country] = None
            finally:
                page.close()
                
        browser.close()
    return results


def fetch_all_rates(markets: list[dict]) -> dict[str, dict]:
    rates = {}
    tv_to_fetch = {}
    
    for m in markets:
        series = m.get("fred_series")
        tv_symbol = m.get("tv_symbol")
        
        if series:
            rates[m["name"]] = fetch_fred_yield(series) or {}
        elif tv_symbol:
            tv_to_fetch[m["name"]] = tv_symbol
        else:
            rates[m["name"]] = {}  
            
    if tv_to_fetch:
        tv_rates = fetch_tv_yields(tv_to_fetch)
        rates.update(tv_rates)
        
    return rates
