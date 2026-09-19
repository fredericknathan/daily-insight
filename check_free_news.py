import feedparser
import urllib.parse
from datetime import datetime, timezone
import time
import requests

def check_google_news_rss(query):
    print(f"\n[Google News RSS] Query: {query}")
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}+when:1d&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    if not feed.entries:
        print("  No results found.")
        return
    for entry in feed.entries[:3]:
        pub_date = entry.published
        print(f"  - {entry.title[:80]}... | {pub_date}")

def check_duckduckgo(query):
    print(f"\n[DuckDuckGo Search] Query: {query}")
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=3, timelimit='d'))
            if not results:
                print("  No results found.")
                return
            for r in results:
                print(f"  - {r.get('title')[:80]}... | {r.get('date')}")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == '__main__':
    queries = ["Vietnam stock market", "Philippines PSEi", "Indonesia JKSE market"]
    for q in queries:
        check_google_news_rss(q)
        check_duckduckgo(q)
