"""
AIHUISHOU URL SCRAPER
Pass any URL - output raw JSON data

Usage:
    python url_scraper.py <url>
    python url_scraper.py "https://m.aihuishou.com/n/#/category?frontCategoryId=6"
"""

import sys
import io
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class UrlScraper:
    """Scrape any URL and capture all API data"""
    
    def __init__(self):
        self.captured_data = []  # All captured API responses
    
    async def scrape(self, url: str, headless: bool = True, scroll_times: int = 5):
        """Scrape URL and capture all API responses"""
        from playwright.async_api import async_playwright
        
        print("=" * 60)
        print("  AIHUISHOU URL SCRAPER")
        print("=" * 60)
        print(f"URL: {url}")
        print("-" * 60)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
                viewport={"width": 375, "height": 812},
                locale="zh-CN"
            )
            
            await context.add_cookies([{
                "name": "chosenCity",
                "value": "%7B%22id%22%3A1%2C%22name%22%3A%22%E4%B8%8A%E6%B5%B7%E5%B8%82%22%7D",
                "domain": "m.aihuishou.com",
                "path": "/"
            }])
            
            page = await context.new_page()
            page.on("response", lambda r: asyncio.create_task(self._capture(r)))
            
            try:
                print("\n[1] Loading page...")
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(5)
                
                print(f"    Captured: {len(self.captured_data)} API responses")
                
                print("\n[2] Scrolling...")
                for i in range(scroll_times):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1.5)
                    print(f"    Scroll {i+1}: {len(self.captured_data)} responses")
                
            except Exception as e:
                print(f"[ERROR] {e}")
            finally:
                await browser.close()
        
        return self.captured_data
    
    async def _capture(self, response):
        """Capture all API responses from dubai.aihuishou.com"""
        if "dubai.aihuishou.com" not in response.url:
            return
        
        try:
            data = await response.json()
            if data.get("code") == 0 and data.get("data"):
                self.captured_data.append(data.get("data"))
        except:
            pass


def export_json(data: List[Any], filename: str = None):
    """Export to JSON"""
    if not filename:
        filename = f"aihuishou_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n[EXPORTED] {filename}")
    return filename


async def main():
    if len(sys.argv) < 2:
        print("Usage: python url_scraper.py <url>")
        print("Example: python url_scraper.py \"https://m.aihuishou.com/n/#/category?frontCategoryId=6\"")
        return
    
    url = sys.argv[1]
    scraper = UrlScraper()
    data = await scraper.scrape(url, headless=False)
    
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"  Total API responses: {len(data)}")
    
    if data:
        export_json(data)
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
