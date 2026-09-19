"""
PHASE 0 SMOKE TEST — run this FIRST, before anything else in this repo.

What it does:
  1. Calls `fetch_all` from `src.fetch.primary` which tests `yfinance` pricing 
     and Google News RSS.
  2. Prints a clear PASS/FAIL/UNKNOWN per country so you know exactly
     where you stand after ~5 minutes.

Run it locally or in GitHub Actions:

    python tests/test_smoke_tickers.py
"""

import json
import yaml
from dataclasses import asdict

from src.fetch.primary import fetch_all

def main():
    print("Loading config...")
    with open("src/config/markets.yaml") as f:
        config = yaml.safe_load(f)
    
    markets = config["countries"]
    
    print("\n[primary] Probing yfinance and Google News RSS for all markets...")
    results = fetch_all(markets)

    print("\n" + "=" * 80)
    print(f"{'Country':<13}{'Status':<10}{'Price':<12}{'Chg %':<8}{'News Count':<12}")
    print("=" * 80)
    
    out_results = []
    
    for m in markets:
        name = m["name"]
        res = results.get(name)
        if res:
            status = "PASS"
            price = str(res.price)
            chg = f"{res.change_pct}%" if res.change_pct is not None else "N/A"
            news = len(res.news_headlines)
            out_results.append(asdict(res))
        else:
            status = "FAIL"
            price = "N/A"
            chg = "N/A"
            news = 0
            out_results.append({"country": name, "status": "FAIL"})
            
        print(f"{name:<13}{status:<10}{price:<12}{chg:<8}{news:<12}")

    out_path = "tests/phase0_results.json"
    with open(out_path, "w") as f:
        json.dump(out_results, f, indent=2, default=str)
        
    print(f"\nFull detail written to {out_path}")

if __name__ == "__main__":
    main()
