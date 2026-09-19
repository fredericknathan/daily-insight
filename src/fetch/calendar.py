"""
Fetches the 24-hour economic calendar from ForexFactory's XML API.
"""

from __future__ import annotations
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# The free fair economy media XML feed for ForexFactory
FF_XML_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"

def fetch_calendar(target_markets: list[str]) -> list[dict]:
    """
    Fetches the next 24 hours of high/medium impact calendar events for the specified target markets.
    """
    try:
        resp = requests.get(FF_XML_URL, timeout=15)
        resp.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(resp.content)
        
        # Map ForexFactory currency codes to our target countries
        currency_map = {
            "USD": "USA",
            "JPY": "Japan",
            "KRW": "Korea",
            "HKD": "Hong Kong",
            "IDR": "Indonesia",
            "SGD": "Singapore",
            "PHP": "Philippines",
            "VND": "Vietnam",
            "CNY": "China" # Often relevant for HK/Asia
        }
        
        events = []
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        
        for event in root.findall("event"):
            date_str = event.find("date").text
            time_str = event.find("time").text
            
            # Skip all-day or tentative events
            if not time_str or "All Day" in time_str or "Tentative" in time_str:
                continue
                
            try:
                # Format: MM-DD-YYYY and H:MMam/pm (Eastern Time)
                event_date = datetime.strptime(date_str, "%m-%d-%Y").date()
                
                # Only care about today and tomorrow
                if event_date != now.date() and event_date != tomorrow.date():
                    continue
                    
            except Exception as e:
                logger.warning(f"Failed to parse date/time {date_str} {time_str}: {e}")
                continue
                
            impact = event.find("impact").text
            # Skip low impact to reduce noise
            if impact not in ["High", "Medium"]:
                continue
                
            currency = event.find("country").text
            country_name = currency_map.get(currency)
            
            # If not a currency we track, skip
            if not country_name and currency not in ["USD", "CNY", "JPY"]: 
                continue
                
            title = event.find("title").text
            forecast = event.find("forecast").text or ""
            previous = event.find("previous").text or ""
            
            events.append({
                "time": time_str,
                "country": country_name or currency,
                "event": title,
                "period": "", # XML doesn't provide MoM/YoY explicitly, LLM can infer
                "consensus": forecast,
                "prior": previous,
                "impact": impact
            })
            
        return events
    except Exception as e:
        logger.error(f"Failed to fetch ForexFactory calendar: {e}")
        return []
