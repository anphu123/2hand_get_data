"""
AIHUISHOU DEEP SCRAPER v4
Supports both 3-level and 4-level paths:
- 3 levels: Category → Brand → Products (watches, phones)
- 4 levels: Category → Brand → Collection → Products (bags with Birkin, Kelly, etc.)

Auto-detects if brand has collections (spu-collection) or direct products (spu-list)
"""

import sys
import json
import asyncio
import csv
import time
import os
from datetime import datetime
from urllib.parse import urlencode, parse_qs, urlparse
from typing import List, Dict, Optional

os.environ['PYTHONIOENCODING'] = 'utf-8'


def log(level: str, msg: str, indent: int = 0):
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = "  " * indent
        symbols = {"INFO": "ℹ", "OK": "✓", "WARN": "⚠", "ERR": "✗", "TIME": "⏱"}
        symbol = symbols.get(level, "•")
        print(f"[{timestamp}] {prefix}{symbol} {msg}")
    except:
        pass


class DeepScraper:
    """
    Smart Scraper with auto-detection:
    - 3 levels: Category → Brand → Products
    - 4 levels: Category → Brand → Collection → Products
    """
    
    WAIT_PAGE = 2.5
    WAIT_SCROLL = 0.4
    MAX_SCROLL = 5
    
    def __init__(self):
        self.brands: List[Dict] = []
        self.collections: List[Dict] = []  # For 4-level path
        self.products: List[Dict] = []
        self.current_brand: Optional[Dict] = None
        self.current_collection: Optional[Dict] = None
        self.start_time: float = 0
        
        # Category info
        self.front_category_id: Optional[str] = None
        self.category_id: Optional[int] = None
        self.biz_type: int = 2
        
        # Stats
        self.stats = {"brands": 0, "collections": 0, "products": 0, "errors": 0}
    
    async def scrape_all(self, category_url: str, headless: bool = True) -> List[Dict]:
        from playwright.async_api import async_playwright
        
        self.start_time = time.time()
        self._parse_url(category_url)
        
        self._print_banner()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
                viewport={"width": 375, "height": 812},
                locale="zh-CN"
            )
            await self._set_cookies(context)
            page = await context.new_page()
            
            # LEVEL 1: Get Brands
            log("INFO", "LEVEL 1: Getting brands...")
            await self._scrape_brands(page, category_url)
            log("OK", f"Found {len(self.brands)} brands")
            
            if not self.brands:
                log("ERR", "No brands found!")
                await browser.close()
                return self.products
            
            # LEVEL 2+: Products (auto-detect 3 or 4 levels)
            for i, brand in enumerate(self.brands):
                self.current_brand = brand
                brand_name = brand.get('name', 'Unknown')
                log("INFO", f"Brand [{i+1}/{len(self.brands)}] {brand_name}")
                
                # Try spu-collection first (4-level), fallback to spu-list (3-level)
                collections = await self._get_collections(page, brand)
                
                if collections:
                    # 4-level path: Brand → Collections → Products
                    log("INFO", f"Found {len(collections)} collections (4-level)", 1)
                    for j, collection in enumerate(collections):
                        self.current_collection = collection
                        log("INFO", f"Collection [{j+1}/{len(collections)}] {collection.get('title', '')[:30]}", 2)
                        await self._scrape_products_from_collection(page, brand, collection)
                else:
                    # 3-level path: Brand → Products
                    log("INFO", "Direct products (3-level)", 1)
                    await self._scrape_products_direct(page, brand)
            
            await browser.close()
        
        self._print_summary()
        return self.products
    
    def _parse_url(self, url: str):
        """Extract category info from URL"""
        parsed = urlparse(url)
        query = parsed.query or (parsed.fragment.split('?')[1] if '?' in parsed.fragment else '')
        params = parse_qs(query)
        
        self.front_category_id = params.get('subFrontCategoryId', params.get('frontCategoryId', [None]))[0]
        if 'categoryId' in params:
            self.category_id = int(params['categoryId'][0])
        if 'bizType' in params:
            self.biz_type = int(params['bizType'][0])
    
    async def _set_cookies(self, context):
        await context.add_cookies([{
            "name": "chosenCity",
            "value": "%7B%22id%22%3A1%2C%22name%22%3A%22%E4%B8%8A%E6%B5%B7%E5%B8%82%22%7D",
            "domain": "m.aihuishou.com",
            "path": "/"
        }])
    
    async def _scrape_brands(self, page, url: str):
        """Scrape brand list from category page"""
        captured_brands = []
        
        async def capture(response):
            if "aihuishou.com" not in response.url:
                return
            try:
                data = await response.json()
                if data.get("code") != 0:
                    return
                items = data.get("data", [])
                if isinstance(items, list) and len(items) > 0:
                    first = items[0]
                    if isinstance(first, dict):
                        # Capture categoryId
                        if "categoryId" in first and not self.category_id:
                            self.category_id = first.get("categoryId")
                            self.biz_type = first.get("bizType", self.biz_type)
                        # Capture brands
                        if "id" in first and "name" in first and "iconUrl" in first and "productId" not in first:
                            for item in items:
                                if not any(b["id"] == item.get("id") for b in captured_brands):
                                    captured_brands.append({
                                        "id": item.get("id"),
                                        "name": item.get("name"),
                                    })
            except:
                pass
        
        page.on("response", lambda r: asyncio.create_task(capture(r)))
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(self.WAIT_PAGE)
        await self._scroll(page, 3)
        
        self.brands = captured_brands
        self.stats["brands"] = len(self.brands)
    
    async def _get_collections(self, page, brand: Dict) -> List[Dict]:
        """Try to get collections for a brand (4-level path)"""
        collections = []
        
        async def capture(response):
            if "spu-collection" not in response.url:
                return
            try:
                data = await response.json()
                if data.get("code") == 0:
                    items = data.get("data", [])
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and "collectionId" in item:
                                collections.append({
                                    "collectionId": item.get("collectionId"),
                                    "title": item.get("title", ""),
                                    "seriesCode": item.get("seriesCode", ""),
                                    "seriesName": item.get("seriesName", ""),
                                })
            except:
                pass
        
        # Build collection URL
        params = {
            "brandId": brand.get("id"),
            "categoryId": self.category_id or 340,
            "frontCategoryId": self.front_category_id or 166,
            "bizType": self.biz_type,
            "brand": brand.get("name", ""),
            "fullScreen": "true"
        }
        collection_url = f"https://m.aihuishou.com/p/main/recycle/spu-collection?{urlencode(params)}"
        
        page.on("response", lambda r: asyncio.create_task(capture(r)))
        
        try:
            await page.goto(collection_url, timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(1.5)
            await self._scroll(page, 2)
        except:
            pass
        
        self.stats["collections"] += len(collections)
        return collections
    
    async def _scrape_products_from_collection(self, page, brand: Dict, collection: Dict):
        """Scrape products from a specific collection (4-level)"""
        products_before = len(self.products)
        
        async def capture(response):
            await self._capture_products(response, brand, collection)
        
        params = {
            "brandId": brand.get("id"),
            "categoryId": self.category_id or 340,
            "frontCategoryId": self.front_category_id or 166,
            "bizType": self.biz_type,
            "brand": brand.get("name", ""),
            "collectionId": collection.get("collectionId"),
            "seriesCode": collection.get("seriesCode", ""),
            "title": collection.get("title", ""),
            "fullScreen": "true"
        }
        spu_url = f"https://m.aihuishou.com/p/main/recycle/spu-list?{urlencode(params)}"
        
        page.on("response", lambda r: asyncio.create_task(capture(r)))
        
        try:
            await page.goto(spu_url, timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(self.WAIT_PAGE)
            await self._scroll(page, self.MAX_SCROLL)
        except Exception as e:
            log("ERR", f"Error: {str(e)[:30]}", 3)
            self.stats["errors"] += 1
        
        added = len(self.products) - products_before
        if added > 0:
            log("OK", f"+{added} products", 3)
    
    async def _scrape_products_direct(self, page, brand: Dict):
        """Scrape products directly from brand (3-level)"""
        products_before = len(self.products)
        
        async def capture(response):
            await self._capture_products(response, brand, None)
        
        params = {
            "brandId": brand.get("id"),
            "categoryId": self.category_id or 138,
            "frontCategoryId": self.front_category_id or 145,
            "bizType": self.biz_type,
            "brand": brand.get("name", ""),
            "fullScreen": "true"
        }
        spu_url = f"https://m.aihuishou.com/p/main/recycle/spu-list?{urlencode(params)}"
        
        page.on("response", lambda r: asyncio.create_task(capture(r)))
        
        try:
            await page.goto(spu_url, timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(self.WAIT_PAGE)
            await self._scroll(page, self.MAX_SCROLL)
        except Exception as e:
            log("ERR", f"Error: {str(e)[:30]}", 2)
            self.stats["errors"] += 1
        
        added = len(self.products) - products_before
        if added > 0:
            log("OK", f"+{added} products", 2)
    
    async def _capture_products(self, response, brand: Dict, collection: Optional[Dict]):
        """Capture product data from API response"""
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
            if not isinstance(first, dict) or "productId" not in first:
                return
            
            for item in items:
                serials = item.get("serials", {})
                series_name = serials.get("name", "") if isinstance(serials, dict) else ""
                
                product = {
                    "brand": brand.get("name", ""),
                    "series": series_name,
                    "collection": collection.get("title", "") if collection else "",
                    "productName": item.get("productName") or item.get("title", ""),
                    "productId": item.get("productId"),
                    "subTitle": item.get("subTitle", ""),
                    "imageUrl": item.get("imageUrl", ""),
                }
                
                if not any(p["productId"] == product["productId"] for p in self.products):
                    self.products.append(product)
                    self.stats["products"] += 1
        except:
            pass
    
    async def _scroll(self, page, times: int = 3):
        """Scroll page to load more content"""
        for _ in range(times):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(self.WAIT_SCROLL)
    
    def _print_banner(self):
        print()
        print("=" * 60)
        print("  AIHUISHOU DEEP SCRAPER v4")
        print("  Supports 3-level and 4-level paths")
        print("=" * 60)
        log("INFO", f"frontCategoryId: {self.front_category_id}")
        log("INFO", f"categoryId: {self.category_id}")
        print()
    
    def _print_summary(self):
        elapsed = time.time() - self.start_time
        print()
        print("=" * 60)
        log("TIME", f"Total time: {elapsed:.1f}s")
        log("OK", f"Brands: {self.stats['brands']}")
        log("OK", f"Collections: {self.stats['collections']}")
        log("OK", f"Products: {self.stats['products']}")
        if self.stats['errors']:
            log("WARN", f"Errors: {self.stats['errors']}")
        print("=" * 60)
        print(f"  Speed: {self.stats['products'] / elapsed:.1f} products/sec")
        print("=" * 60)


def export_csv(products: list, filename: str = None):
    if not filename:
        filename = f"deep_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    if not products:
        log("WARN", "No products!")
        return None
    
    fieldnames = ['brand', 'series', 'collection', 'productName', 'subTitle', 'productId', 'imageUrl']
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
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
        print()
        print("Examples:")
        print('  # Watches (3-level):')
        print('  python deep_scraper.py "https://m.aihuishou.com/n/#/category?frontCategoryId=144&subFrontCategoryId=145"')
        print()
        print('  # Bags (4-level):')
        print('  python deep_scraper.py "https://m.aihuishou.com/n/#/category?frontCategoryId=165&subFrontCategoryId=166"')
        return
    
    url = sys.argv[1]
    headless = "--show" not in sys.argv
    
    scraper = DeepScraper()
    products = await scraper.scrape_all(url, headless=headless)
    
    if products:
        export_csv(products)
        export_json(products)
        
        print()
        print(f"✅ RESULTS: {len(products)} products scraped!")
    else:
        log("ERR", "No products found!")


if __name__ == "__main__":
    asyncio.run(main())
