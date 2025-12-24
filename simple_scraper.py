"""
AIHUISHOU SIMPLE SCRAPER
Scrape data by browsing website and capturing API responses
No hash code - just direct data extraction

Usage:
    python simple_scraper.py [category_id] [brand_name]
    python simple_scraper.py 6           # Phones category
    python simple_scraper.py 6 Apple     # Phones + Apple brand
"""

import sys
import io
import json
import asyncio
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class SimpleScraper:
    """Simple scraper - browse and capture API data"""
    
    def __init__(self):
        self.categories = []
        self.brands = []
        self.products = []
    
    async def scrape(self, category_id: int = 6, brand_name: Optional[str] = None, headless: bool = True):
        """Scrape data from category"""
        from playwright.async_api import async_playwright
        
        print("=" * 50)
        print("  AIHUISHOU SCRAPER")
        print("=" * 50)
        print(f"Category ID: {category_id}")
        print(f"Brand filter: {brand_name or 'All'}")
        print(f"Headless: {headless}")
        print("-" * 50)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
                viewport={"width": 375, "height": 812},
                locale="zh-CN"
            )
            
            # Set city cookie
            await context.add_cookies([{
                "name": "chosenCity",
                "value": "%7B%22id%22%3A1%2C%22name%22%3A%22%E4%B8%8A%E6%B5%B7%E5%B8%82%22%7D",
                "domain": "m.aihuishou.com",
                "path": "/"
            }])
            
            page = await context.new_page()
            
            # Capture API responses
            page.on("response", lambda r: asyncio.create_task(self._capture(r)))
            
            try:
                # Go to category page
                url = f"https://m.aihuishou.com/n/#/category?frontCategoryId={category_id}"
                print(f"\n[1] Loading {url}")
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(5)
                
                print(f"    Brands captured: {len(self.brands)}")
                
                # Click brand if specified
                if brand_name and self.brands:
                    target = next((b for b in self.brands if brand_name.lower() in b.get("name", "").lower()), None)
                    if target:
                        print(f"\n[2] Selecting brand: {target.get('name')}")
                        # Click on brand by finding element containing brand name
                        clicked = await page.evaluate(f"""
                            () => {{
                                const items = document.querySelectorAll('*');
                                for (const item of items) {{
                                    const text = item.textContent?.trim();
                                    if (text === '{target.get("name")}' || (text && text.includes('{target.get("name")}') && text.length < 15)) {{
                                        item.click();
                                        return true;
                                    }}
                                }}
                                return false;
                            }}
                        """)
                        if clicked:
                            print("    Brand clicked, waiting for products...")
                            await asyncio.sleep(5)
                        else:
                            print("    Could not find brand element")
                
                # Scroll to load more
                print("\n[3] Scrolling to load products...")
                for i in range(5):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1.5)
                    print(f"    Scroll {i+1}: {len(self.products)} products")
                
            except Exception as e:
                print(f"[ERROR] {e}")
            finally:
                await browser.close()
        
        return {
            "categories": self.categories,
            "brands": self.brands,
            "products": self.products
        }
    
    async def _capture(self, response):
        """Capture API responses"""
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
            
            # Products
            if "maxPrice" in first:
                self.products.extend(items)
            # Brands
            elif "iconUrl" in first and "name" in first:
                self.brands.extend(items)
            # Categories
            elif "frontCategoryId" in first:
                self.categories.extend(items)
        except:
            pass


def export_data(data: Dict, prefix: str = "aihuishou"):
    """Export to files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    products = data.get("products", [])
    if products:
        df = pd.DataFrame([{
            "ID": p.get("id"),
            "Name": p.get("name"),
            "Max Price": p.get("maxPrice"),
            "Brand ID": p.get("brandId"),
            "Image": p.get("imageUrl")
        } for p in products])
        
        excel_file = f"{prefix}_products_{timestamp}.xlsx"
        csv_file = f"{prefix}_products_{timestamp}.csv"
        
        df.to_excel(excel_file, index=False)
        df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        
        print(f"\n[EXPORT] {len(products)} products")
        print(f"  -> {excel_file}")
        print(f"  -> {csv_file}")
    
    brands = data.get("brands", [])
    if brands:
        json_file = f"{prefix}_brands_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(brands, f, ensure_ascii=False, indent=2)
        print(f"  -> {json_file} ({len(brands)} brands)")


async def main():
    # Parse args
    category_id = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    brand_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    scraper = SimpleScraper()
    result = await scraper.scrape(category_id, brand_name, headless=False)
    
    print("\n" + "=" * 50)
    print("  RESULTS")
    print("=" * 50)
    print(f"  Categories: {len(result['categories'])}")
    print(f"  Brands: {len(result['brands'])}")
    print(f"  Products: {len(result['products'])}")
    
    if result["products"]:
        print("\n  TOP 10 PRODUCTS:")
        for p in result["products"][:10]:
            print(f"    {p.get('id'):<8} {p.get('name', 'N/A')[:35]:<37} {p.get('maxPrice', 0):>6} CNY")
    
    # Export
    if result["products"] or result["brands"]:
        export_data(result)
    
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
