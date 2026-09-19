import asyncio
from playwright.async_api import async_playwright

async def test_scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.tradingview.com/symbols/TVC-HK10Y/', wait_until='networkidle')
        
        # Wait for the price to appear
        try:
            await page.wait_for_function("document.querySelector('.js-symbol-last').innerText.trim() !== ''", timeout=5000)
        except Exception:
            pass
            
        price = await page.evaluate("document.querySelector('.js-symbol-last').innerText")
        print(f"Price: {price}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_scrape())
