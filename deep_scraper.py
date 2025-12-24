"""
AIHUISHOU DEEP SCRAPER v3
Category → Brands → Products

Fixed: Extract categoryId/frontCategoryId from category page URL and API
"""

import sys
import json
import asyncio
import csv
import time
import os
import re
from datetime import datetime
from urllib.parse import urlencode, parse_qs, urlparse

os.environ['PYTHONIOENCODING'] = 'utf-8'


def log(level: str, msg: str, indent: int = 0):
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = "  " * indent
        symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[x]", "TIME": "[t]"}
        symbol = symbols.get(level, "•")
        print(f"[{timestamp}] {prefix}{symbol} {msg}")
    except:
        pass


class DeepScraper:
    """Scraper: Category → Brands → Products"""
    
    WAIT_PAGE = 3
    WAIT_SCROLL = 0.5
    
    def __init__(self):
        self.brands = []
        self.products = []
        self.current_brand = None
        self.start_time = None
        # Category info extracted from URL/API
        self.front_category_id = None
        self.category_id = None
        self.biz_type = 2
        
    async def scrape_all(self, category_url: str, headless: bool = True):
        from playwright.async_api import async_playwright
        
        self.start_time = time.time()
        
        # Extract frontCategoryId from URL
        parsed = urlparse(category_url)
        params = parse_qs(parsed.fragment.split('?')[1] if '?' in parsed.fragment else parsed.query)
        self.front_category_id = params.get('subFrontCategoryId', params.get('frontCategoryId', [None]))[0]
        
        print("=" * 60)
        print("  AIHUISHOU DEEP SCRAPER v3")
        print("  Category -> Brands -> Products")
        print("=" * 60)
        log("INFO", f"frontCategoryId: {self.front_category_id}")
        print()
        
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
            
            # ========== LEVEL 1: Get Brands + Category Info ==========
            log("INFO", "LEVEL 1: Getting brands and category info...")
            page.on("response", lambda r: asyncio.create_task(self._capture_category_info(r)))
            page.on("response", lambda r: asyncio.create_task(self._capture_brands(r)))
            
            await page.goto(category_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(self.WAIT_PAGE)
            
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(self.WAIT_SCROLL)
            
            log("OK", f"Found {len(self.brands)} brands")
            log("INFO", f"categoryId: {self.category_id}, frontCategoryId: {self.front_category_id}")
            
            if not self.brands:
                log("ERR", "No brands found!")
                await browser.close()
                return self.products
            
            # ========== LEVEL 2: Products for each brand ==========
            for i, brand in enumerate(self.brands):
                self.current_brand = brand
                brand_name = brand.get('name', 'Unknown')
                
                log("INFO", f"Brand [{i+1}/{len(self.brands)}] {brand_name}")
                
                spu_url = self._build_spu_url(brand)
                log("INFO", f"URL: {spu_url[:80]}...", 1)
                
                page.on("response", lambda r: asyncio.create_task(self._capture_products(r)))
                
                try:
                    t = time.time()
                    products_before = len(self.products)
                    
                    await page.goto(spu_url, timeout=30000, wait_until="domcontentloaded")
                    await asyncio.sleep(self.WAIT_PAGE)
                    
                    # Scroll to load more
                    for _ in range(5):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(self.WAIT_SCROLL)
                    
                    await asyncio.sleep(0.5)
                    products_added = len(self.products) - products_before
                    log("OK", f"+{products_added} products ({time.time()-t:.1f}s)", 1)
                    
                except Exception as e:
                    log("ERR", f"Error: {str(e)[:40]}", 1)
            
            await browser.close()
        
        total_time = time.time() - self.start_time
        print()
        log("TIME", f"Total: {total_time:.1f}s")
        log("OK", f"Total products: {len(self.products)}")
        
        return self.products
    
    def _build_spu_url(self, brand: dict) -> str:
        """Build SPU list URL using extracted category info"""
        params = {
            "brandId": brand.get("id", ""),
            "categoryId": self.category_id or 138,  # Default to 138 if not found
            "frontCategoryId": self.front_category_id or 145,
            "bizType": self.biz_type,
            "brand": brand.get("name", ""),
            "fullScreen": "true"
        }
        return f"https://m.aihuishou.com/p/main/recycle/spu-list?{urlencode(params)}"
    
    async def _capture_category_info(self, response):
        """Capture categoryId from API responses"""
        if "aihuishou.com" not in response.url:
            return
        try:
            data = await response.json()
            if data.get("code") != 0:
                return
            
            items = data.get("data", [])
            
            # Look for front-category-by-brand response
            if isinstance(items, list) and len(items) > 0:
                first = items[0]
                if isinstance(first, dict):
                    # Pattern: frontCategoryId + categoryId in response
                    if "frontCategoryId" in first and "categoryId" in first:
                        self.front_category_id = self.front_category_id or first.get("frontCategoryId")
                        self.category_id = first.get("categoryId")
                        if "bizType" in first:
                            self.biz_type = first.get("bizType")
                        log("INFO", f"Found categoryId={self.category_id} from API", 1)
        except:
            pass
    
    async def _capture_brands(self, response):
        """Capture brand list"""
        if "aihuishou.com" not in response.url:
            return
        try:
            data = await response.json()
            if data.get("code") != 0:
                return
            
            items = data.get("data", [])
            if not isinstance(items, list) or not items:
                return
            
            first = items[0]
            if not isinstance(first, dict):
                return
                
            # Brand: id, name, iconUrl (no productId)
            if "id" in first and "name" in first and "iconUrl" in first and "productId" not in first:
                for item in items:
                    brand_info = {
                        "id": item.get("id"),
                        "name": item.get("name"),
                    }
                    if not any(b["id"] == brand_info["id"] for b in self.brands):
                        self.brands.append(brand_info)
        except:
            pass
    
    async def _capture_products(self, response):
        """Capture products"""
        if "aihuishou.com" not in response.url:
            return
        try:
            data = await response.json()
            if data.get("code") != 0:
                return
            
            items = data.get("data", [])
            if not isinstance(items, list) or not items:
                return
            
            first = items[0]
            if not isinstance(first, dict):
                return
            
            if "productId" in first:
                brand_name = self.current_brand.get("name", "") if self.current_brand else ""
                
                for item in items:
                    serials = item.get("serials", {})
                    series_name = serials.get("name", "") if isinstance(serials, dict) else ""
                    
                    product = {
                        "brand": brand_name,
                        "series": series_name,
                        "productName": item.get("productName") or item.get("title", ""),
                        "productId": item.get("productId"),
                        "subTitle": item.get("subTitle", ""),
                        "imageUrl": item.get("imageUrl", ""),
                    }
                    
                    if not any(p["productId"] == product["productId"] for p in self.products):
                        self.products.append(product)
        except:
            pass


def export_csv(products: list, filename: str = None):
    if not filename:
        filename = f"deep_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    if not products:
        log("WARN", "No products!")
        return None
    
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['brand', 'series', 'productName', 'subTitle', 'productId', 'imageUrl'])
        writer.writeheader()
        writer.writerows(products)
    
    log("OK", f"Exported: {filename}")
    return filename


def export_json(products: list, filename: str = None):
    if not filename:
        filename = f"deep_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    log("OK", f"Exported: {filename}")
    return filename


async def main():
    if len(sys.argv) < 2:
        print("Usage: python deep_scraper.py <category_url>")
        print('Example: python deep_scraper.py "https://m.aihuishou.com/n/#/category?frontCategoryId=144&subFrontCategoryId=145"')
        return
    
    url = sys.argv[1]
    headless = "--show" not in sys.argv
    
    scraper = DeepScraper()
    products = await scraper.scrape_all(url, headless=headless)
    
    if products:
        export_csv(products)
        export_json(products)
        
        print()
        print("=" * 60)
        print(f"  RESULTS: {len(products)} products")
        print("=" * 60)
    else:
        log("ERR", "No products found!")


if __name__ == "__main__":
    asyncio.run(main())
