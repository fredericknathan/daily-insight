import asyncio
from playwright.async_api import async_playwright
import re

async def test_scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.tradingview.com/symbols/TVC-HK10Y/', wait_until='domcontentloaded')
        html = await page.content()
        
        # Look for the span that contains the last price
        prices = re.findall(r'class="[^"]*last[^"]*"[^>]*>([^<]+)<', html)
        print('Prices found in last classes:', prices)
        
        # Or just search for the specific text structure
        import bs4
        soup = bs4.BeautifulSoup(html, 'html.parser')
        
        # In TradingView, the main price is usually in a div with a class containing 'priceWrapper' or similar
        # Let's find all spans with a class containing 'last' or 'price'
        candidates = soup.select('span[class*="last"], div[class*="priceWrapper"] span')
        for c in candidates[:10]:
            print(f"Candidate: {c.get('class')} -> {c.text.strip()}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_scrape())
