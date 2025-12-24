"""
DEBUG: Check what brand data contains from category page
"""

import asyncio


async def test():
    from playwright.async_api import async_playwright
    
    category_url = "https://m.aihuishou.com/n/#/category?frontCategoryId=144&subFrontCategoryId=145"
    
    brands = []
    
    async def capture(response):
        if "aihuishou.com" not in response.url:
            return
        try:
            data = await response.json()
            if data.get("code") == 0:
                items = data.get("data", [])
                if isinstance(items, list) and len(items) > 0:
                    first = items[0]
                    if isinstance(first, dict):
                        # Check if it's brand data
                        if "id" in first and "name" in first and "iconUrl" in first:
                            print(f"\n=== BRAND DATA FOUND ===")
                            print(f"Count: {len(items)}")
                            print(f"First brand keys: {list(first.keys())}")
                            print(f"First brand: {first}")
                            brands.extend(items)
        except:
            pass
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
            viewport={"width": 375, "height": 812}
        )
        
        await context.add_cookies([{
            "name": "chosenCity",
            "value": "%7B%22id%22%3A1%2C%22name%22%3A%22%E4%B8%8A%E6%B5%B7%E5%B8%82%22%7D",
            "domain": "m.aihuishou.com",
            "path": "/"
        }])
        
        page = await context.new_page()
        page.on("response", lambda r: asyncio.create_task(capture(r)))
        
        print(f"Opening category page...")
        await page.goto(category_url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(4)
        
        for _ in range(3):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.5)
        
        await browser.close()
    
    print(f"\n=== TOTAL: {len(brands)} brands ===")


if __name__ == "__main__":
    asyncio.run(test())
