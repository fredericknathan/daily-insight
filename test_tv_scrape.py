import asyncio
from playwright.async_api import async_playwright

async def test_scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to TradingView HK 10Y...")
        try:
            resp = await page.goto("https://www.tradingview.com/symbols/TVC-HK10Y/", wait_until="domcontentloaded", timeout=15000)
            print(f"Status: {resp.status}")
            
            # Look for the price element. On TradingView symbol pages, the last price is usually in a class like "js-symbol-last" or "symbol-last"
            # We can just dump the page title and see if it loaded.
            title = await page.title()
            print(f"Title: {title}")
            
            # Dump a snippet of text to see if we got blocked
            text = await page.evaluate('document.body.innerText')
            print(f"Body snippet: {text[:200]}")
        except Exception as e:
            print(f"Failed: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_scrape())
