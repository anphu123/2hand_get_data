"""
AIHUISHOU FULL FLOW SCRAPER
Category -> Brand -> Products with UI automation

Usage:
    python flow_scraper.py
"""

import sys
import io
import json
import asyncio
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class FlowScraper:
    """Scraper that follows Category -> Brand -> Products flow"""
    
    def __init__(self):
        self.categories = []
        self.brands = []
        self.products = []
    
    async def run(self, target_category: str = None, target_brand: str = None):
        """Run the full scraping flow"""
        from playwright.async_api import async_playwright
        
        print("=" * 60)
        print("  AIHUISHOU FLOW SCRAPER")
        print("  Category -> Brand -> Products")
        print("=" * 60)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Show browser
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
                viewport={"width": 375, "height": 812},
                locale="zh-CN"
            )
            
            # Set cookies
            await context.add_cookies([{
                "name": "chosenCity",
                "value": "%7B%22id%22%3A1%2C%22name%22%3A%22%E4%B8%8A%E6%B5%B7%E5%B8%82%22%7D",
                "domain": "m.aihuishou.com",
                "path": "/"
            }])
            
            page = await context.new_page()
            
            # Capture API responses
            page.on("response", lambda r: asyncio.create_task(self._handle_response(r)))
            
            try:
                # Step 1: Go to Phones category (frontCategoryId=6)
                category_url = f"https://m.aihuishou.com/n/#/category?frontCategoryId=6"
                print(f"\n[STEP 1] Loading phones category...")
                print(f"[URL] {category_url}")
                await page.goto(category_url, timeout=30000)
                await asyncio.sleep(4)
                
                # Wait for brands to load
                print("\n[STEP 2] Waiting for brands to load...")
                await asyncio.sleep(2)
                
                # Check captured brands
                if self.brands:
                    print(f"[INFO] Captured {len(self.brands)} brands from API")
                    for b in self.brands[:10]:
                        print(f"  - {b.get('name')} (ID: {b.get('id')})")
                
                # Step 3: Click on Apple brand
                print("\n[STEP 3] Looking for Apple brand...")
                apple_clicked = await page.evaluate("""
                    () => {
                        const items = document.querySelectorAll('*');
                        for (const item of items) {
                            const text = item.textContent?.trim() || '';
                            // Find element containing 苹果 but not too much text
                            if (text === '苹果' || (text.includes('苹果') && text.length < 10)) {
                                item.click();
                                return 'Apple clicked';
                            }
                        }
                        // Try clicking on first brand image/icon
                        const icons = document.querySelectorAll('img[alt*="苹果"], img[src*="apple"], [class*="brand"] img');
                        if (icons.length > 0) {
                            icons[0].click();
                            return 'Apple icon clicked';
                        }
                        return null;
                    }
                """)
                if apple_clicked:
                    print(f"[OK] {apple_clicked}")
                    await asyncio.sleep(4)
                
                # Step 4: Click on target brand (or Apple)
                if target_brand:
                    brand_text = target_brand
                elif self.brands:
                    brand_text = self.brands[0].get('name', '苹果')
                else:
                    brand_text = "苹果"
                
                print(f"\n[STEP 4] Clicking brand: {brand_text}")
                brand_clicked = await page.evaluate(f"""
                    (text) => {{
                        const items = document.querySelectorAll('[class*="brand"], [class*="item"], a, span, div, img');
                        for (const item of items) {{
                            const itemText = item.textContent?.trim() || item.alt || '';
                            if (itemText.includes(text)) {{
                                item.click();
                                return itemText;
                            }}
                        }}
                        return null;
                    }}
                """, brand_text)
                
                if brand_clicked:
                    print(f"[OK] Clicked on: {brand_clicked}")
                    await asyncio.sleep(5)
                
                # Step 5: Scroll to load products
                print("\n[STEP 5] Scrolling to load products...")
                for i in range(5):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1.5)
                    print(f"  Scroll {i+1}/5 - {len(self.products)} products captured")
                
                # Take screenshot
                screenshot = f"flow_result_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot(path=screenshot)
                print(f"\n[SCREENSHOT] Saved to {screenshot}")
                
                # Wait for user to see result
                print("\n[INFO] Browser will stay open for 10 seconds...")
                await asyncio.sleep(10)
                
            except Exception as e:
                print(f"[ERROR] {e}")
            finally:
                await browser.close()
        
        # Return results
        return {
            "categories": self.categories,
            "brands": self.brands,
            "products": self.products
        }
    
    async def _handle_response(self, response):
        """Capture API responses"""
        url = response.url
        if "dubai.aihuishou.com" not in url:
            return
        
        try:
            data = await response.json()
            if data.get("code") != 0:
                return
            
            resp_data = data.get("data")
            
            if isinstance(resp_data, list) and len(resp_data) > 0:
                first = resp_data[0]
                
                # Products (has maxPrice)
                if "maxPrice" in first:
                    self.products.extend(resp_data)
                    print(f"[CAPTURED] {len(resp_data)} products!")
                
                # Brands (has iconUrl)
                elif "iconUrl" in first and "name" in first:
                    self.brands.extend(resp_data)
                    print(f"[CAPTURED] {len(resp_data)} brands")
                
                # Categories
                elif "frontCategoryId" in first:
                    self.categories.extend(resp_data)
                    print(f"[CAPTURED] {len(resp_data)} categories")
                    
        except:
            pass


def export_results(data: Dict):
    """Export results to files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if data.get("products"):
        products = data["products"]
        df = pd.DataFrame([{
            "ID": p.get("id"),
            "Name": p.get("name"),
            "Max Price": p.get("maxPrice"),
            "Brand ID": p.get("brandId"),
            "Image": p.get("imageUrl")
        } for p in products])
        
        excel_file = f"products_{timestamp}.xlsx"
        csv_file = f"products_{timestamp}.csv"
        
        df.to_excel(excel_file, index=False)
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"\n[EXPORTED] {len(products)} products")
        print(f"  Excel: {excel_file}")
        print(f"  CSV: {csv_file}")
    
    if data.get("brands"):
        brands = data["brands"]
        json_file = f"brands_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(brands, f, ensure_ascii=False, indent=2)
        print(f"  Brands JSON: {json_file}")


async def main():
    # Get optional arguments
    target_category = sys.argv[1] if len(sys.argv) > 1 else None
    target_brand = sys.argv[2] if len(sys.argv) > 2 else None
    
    scraper = FlowScraper()
    result = await scraper.run(target_category, target_brand)
    
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"  Categories: {len(result['categories'])}")
    print(f"  Brands: {len(result['brands'])}")
    print(f"  Products: {len(result['products'])}")
    
    if result['products']:
        print("\n  TOP PRODUCTS:")
        for p in result['products'][:10]:
            print(f"    {p.get('id'):<8} {p.get('name', 'N/A')[:35]:<37} {p.get('maxPrice', 0):>6} CNY")
    
    print("=" * 60)
    
    if result['products'] or result['brands']:
        export_results(result)


if __name__ == "__main__":
    asyncio.run(main())
