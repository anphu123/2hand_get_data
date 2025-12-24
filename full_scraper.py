"""
AIHUISHOU FULL DATA SCRAPER
Scrape all categories with brands in structured JSON format
Output format matches existing JSON files

Usage:
    python full_scraper.py
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


# Category IDs to scrape
CATEGORIES = {
    6: "Phones",
    7: "Laptops", 
    8: "Tablets",
    10: "Cameras",
    107: "Shoes",
    108: "Clothes",
    206: "Bags",
    144: "Watches",
}


class FullScraper:
    """Scrape all categories with brands - output structured JSON"""
    
    def __init__(self):
        self.all_data = []  # [{frontCategoryId, groups: [{groupName, details}]}]
        self.current_category = None
        self.current_brands = []
    
    async def scrape_all(self, headless: bool = True):
        """Scrape all categories"""
        from playwright.async_api import async_playwright
        
        print("=" * 60)
        print("  AIHUISHOU FULL DATA SCRAPER")
        print("  Scraping all categories with brands")
        print("=" * 60)
        
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
            
            for cat_id, cat_name in CATEGORIES.items():
                print(f"\n[{cat_name}] Category ID: {cat_id}")
                self.current_category = cat_id
                self.current_brands = []
                
                try:
                    url = f"https://m.aihuishou.com/n/#/category?frontCategoryId={cat_id}"
                    await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    await asyncio.sleep(4)
                    
                    # Wait for brands to load
                    await asyncio.sleep(2)
                    
                    if self.current_brands:
                        # Structure data like existing JSON
                        category_data = {
                            "frontCategoryId": cat_id,
                            "groups": [{
                                "groupName": "Hot Brands",
                                "details": self.current_brands
                            }]
                        }
                        self.all_data.append(category_data)
                        print(f"    Captured {len(self.current_brands)} brands")
                    else:
                        print(f"    No brands found")
                        
                except Exception as e:
                    print(f"    Error: {e}")
            
            await browser.close()
        
        return self.all_data
    
    async def _capture(self, response):
        """Capture brand data from API"""
        if "dubai.aihuishou.com" not in response.url:
            return
        
        try:
            data = await response.json()
            if data.get("code") != 0:
                return
            
            items = data.get("data", [])
            if not isinstance(items, list) or not items:
                return
            
            first = items[0]
            
            # Brands (has iconUrl and name)
            if "iconUrl" in first and "name" in first and "maxPrice" not in first:
                # Format like existing JSON
                formatted_brands = [{
                    "id": b.get("id"),
                    "name": b.get("name"),
                    "iconUrl": b.get("iconUrl"),
                    "marketingTagText": b.get("marketingTagText")
                } for b in items]
                self.current_brands = formatted_brands
        except:
            pass


def export_json(data: List[Dict], filename: str = None):
    """Export to JSON file"""
    if not filename:
        filename = f"aihuishou_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n[EXPORTED] {filename}")
    return filename


async def main():
    scraper = FullScraper()
    data = await scraper.scrape_all(headless=False)
    
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"  Total categories: {len(data)}")
    
    total_brands = sum(len(cat.get("groups", [{}])[0].get("details", [])) for cat in data)
    print(f"  Total brands: {total_brands}")
    
    if data:
        export_json(data)
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
