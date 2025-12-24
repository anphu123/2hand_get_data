"""
AIHUISHOU UNIVERSAL SCRAPER
Nhap bat ky link nao tu aihuishou.com, tool se tu dong lay data

Usage:
    python scraper.py [URL]
    
Examples:
    python scraper.py "https://m.aihuishou.com/n/#/inquiry?productId=43510"
    python scraper.py "https://m.aihuishou.com/n/#/category?frontCategoryId=6"
    python scraper.py "https://m.aihuishou.com/n/#/category?frontCategoryId=144&subFrontCategoryId=145"
"""

import re
import sys
import io
import json
import asyncio
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class AihuishouScraper:
    """Universal scraper cho aihuishou.com"""
    
    def __init__(self):
        self.captured_data = {
            "products": [],
            "brands": [],
            "inquiry": None,
            "raw_responses": []
        }
    
    async def scrape(self, url: str) -> Dict[str, Any]:
        """Main scrape function - tu dong detect loai URL"""
        from playwright.async_api import async_playwright
        
        print(f"\n[URL] {url}")
        
        # Detect URL type
        url_type = self._detect_url_type(url)
        print(f"[TYPE] {url_type}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
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
            
            # Setup response interceptor
            page.on("response", lambda r: asyncio.create_task(self._handle_response(r)))
            
            try:
                print("[INFO] Loading page...")
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(4)
                
                # For category pages, try to click on first brand to get products
                if url_type == "category" and not self.captured_data["products"]:
                    print("[INFO] Trying to click on a brand to get products...")
                    try:
                        # Wait for brand items to load
                        await asyncio.sleep(2)
                        
                        # Try clicking Apple or first brand
                        clicked = await page.evaluate("""
                            () => {
                                // Find all clickable brand items
                                const items = document.querySelectorAll('[class*="brand"], [class*="item"], a, li');
                                for (const item of items) {
                                    const text = item.textContent || '';
                                    // Prefer Apple brand
                                    if (text.includes('苹果') || text.includes('Apple')) {
                                        item.click();
                                        return 'Apple';
                                    }
                                }
                                // Otherwise click first item with a brand name
                                for (const item of items) {
                                    const text = item.textContent || '';
                                    if (text.length > 0 && text.length < 20 && !text.includes('\\n')) {
                                        item.click();
                                        return text.trim().substring(0, 15);
                                    }
                                }
                                return null;
                            }
                        """)
                        
                        if clicked:
                            print(f"[INFO] Clicked brand: {clicked}")
                            # Wait for products to load
                            await asyncio.sleep(4)
                    except Exception as e:
                        print(f"[DEBUG] Brand click failed: {e}")
                
                # Scroll to load more data
                print("[INFO] Scrolling to load more...")
                for i in range(5):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1.5)
                    if self.captured_data["products"]:
                        print(f"[DATA] {len(self.captured_data['products'])} products captured")
                
                # Take screenshot for debugging
                screenshot_path = f"debug_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot(path=screenshot_path)
                
            except Exception as e:
                print(f"[ERROR] {e}")
            finally:
                await browser.close()
        
        return self._prepare_result(url_type)
    
    def _detect_url_type(self, url: str) -> str:
        """Detect loai URL"""
        if "inquiry" in url or "productId" in url:
            return "product_inquiry"
        elif "category" in url:
            if "brandId" in url:
                return "brand_products"
            elif "subFrontCategoryId" in url:
                return "sub_category"
            else:
                return "category"
        elif "brand" in url:
            return "brand"
        elif "spu-list" in url:
            return "spu_list"
        else:
            return "unknown"
    
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
            
            # Save raw response for inspection
            self.captured_data["raw_responses"].append({
                "url": url[:100],
                "data_type": type(resp_data).__name__,
                "sample": str(resp_data)[:200] if resp_data else None
            })
            
            # Product list (has id, name, maxPrice)
            if isinstance(resp_data, list) and len(resp_data) > 0:
                first = resp_data[0]
                
                if all(k in first for k in ["id", "name", "maxPrice"]):
                    self.captured_data["products"].extend(resp_data)
                    print(f"[CAPTURED] {len(resp_data)} products")
                
                elif all(k in first for k in ["id", "name", "iconUrl"]):
                    self.captured_data["brands"].extend(resp_data)
                    print(f"[CAPTURED] {len(resp_data)} brands")
            
            # Product inquiry response
            elif isinstance(resp_data, dict):
                if "productName" in resp_data or "quickInquiry" in resp_data:
                    self.captured_data["inquiry"] = resp_data
                    print(f"[CAPTURED] Product inquiry: {resp_data.get('productName')}")
                
                elif "brands" in resp_data:
                    self.captured_data["brands"].extend(resp_data.get("brands", []))
                    print(f"[CAPTURED] {len(resp_data.get('brands', []))} brands")
                    
        except Exception as e:
            pass
    
    def _prepare_result(self, url_type: str) -> Dict[str, Any]:
        """Prepare final result"""
        result = {
            "type": url_type,
            "success": False,
            "products": [],
            "brands": [],
            "inquiry": None,
            "total": 0
        }
        
        if self.captured_data["products"]:
            result["products"] = self.captured_data["products"]
            result["total"] = len(self.captured_data["products"])
            result["success"] = True
        
        if self.captured_data["brands"]:
            result["brands"] = self.captured_data["brands"]
            if not result["success"]:
                result["total"] = len(self.captured_data["brands"])
                result["success"] = True
        
        if self.captured_data["inquiry"]:
            result["inquiry"] = self.captured_data["inquiry"]
            result["success"] = True
        
        # Debug info
        result["_debug"] = self.captured_data["raw_responses"]
        
        return result


def export_data(data: Dict, prefix: str = "aihuishou"):
    """Export data to Excel/CSV/JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Export products
    if data.get("products"):
        products = data["products"]
        rows = []
        for p in products:
            rows.append({
                "ID": p.get("id"),
                "Name": p.get("name"),
                "Max Price (CNY)": p.get("maxPrice"),
                "Brand ID": p.get("brandId"),
                "Category ID": p.get("categoryId"),
                "Image URL": p.get("imageUrl"),
                "Biz Type": p.get("bizType"),
                "Marketing Tag": p.get("marketingTagText")
            })
        
        df = pd.DataFrame(rows)
        
        excel_file = f"{prefix}_products_{timestamp}.xlsx"
        csv_file = f"{prefix}_products_{timestamp}.csv"
        json_file = f"{prefix}_products_{timestamp}.json"
        
        df.to_excel(excel_file, index=False, engine='openpyxl')
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        print(f"\n[EXPORTED] {len(products)} products")
        print(f"  Excel: {excel_file}")
        print(f"  CSV:   {csv_file}")
        print(f"  JSON:  {json_file}")
        return
    
    # Export brands
    if data.get("brands"):
        brands = data["brands"]
        df = pd.DataFrame(brands)
        
        excel_file = f"{prefix}_brands_{timestamp}.xlsx"
        csv_file = f"{prefix}_brands_{timestamp}.csv"
        
        df.to_excel(excel_file, index=False, engine='openpyxl')
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"\n[EXPORTED] {len(brands)} brands")
        print(f"  Excel: {excel_file}")
        print(f"  CSV:   {csv_file}")
        return
    
    # Export inquiry
    if data.get("inquiry"):
        inquiry = data["inquiry"]
        json_file = f"{prefix}_inquiry_{timestamp}.json"
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(inquiry, f, ensure_ascii=False, indent=2)
        
        print(f"\n[EXPORTED] Product inquiry")
        print(f"  JSON: {json_file}")
        return
    
    print("\n[WARNING] No data to export")


def print_summary(data: Dict):
    """Print summary of scraped data"""
    print("\n" + "=" * 60)
    print("  SCRAPE RESULT")
    print("=" * 60)
    
    print(f"  Type:    {data.get('type')}")
    print(f"  Success: {data.get('success')}")
    print(f"  Total:   {data.get('total')}")
    
    if data.get("products"):
        print(f"\n  PRODUCTS ({len(data['products'])} items):")
        print("  " + "-" * 56)
        for p in data["products"][:10]:
            name = str(p.get("name", "N/A"))[:35]
            print(f"    {p.get('id'):<8} {name:<37} {p.get('maxPrice', 0):>6} CNY")
        if len(data["products"]) > 10:
            print(f"    ... and {len(data['products']) - 10} more")
    
    if data.get("brands"):
        print(f"\n  BRANDS ({len(data['brands'])} items):")
        print("  " + "-" * 56)
        for b in data["brands"][:10]:
            print(f"    {b.get('id'):<6} {b.get('name')}")
        if len(data["brands"]) > 10:
            print(f"    ... and {len(data['brands']) - 10} more")
    
    if data.get("inquiry"):
        inq = data["inquiry"]
        print(f"\n  INQUIRY:")
        print(f"    Product: {inq.get('productName')}")
        print(f"    ID: {inq.get('productId')}")
        print(f"    Coupon Price: {inq.get('couponPrice')} CNY")
    
    print("=" * 60)


async def main():
    print("=" * 60)
    print("  AIHUISHOU UNIVERSAL SCRAPER")
    print("  Nhap bat ky URL nao de lay data")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        # Check if it's a brand ID (number only)
        if arg.isdigit():
            brand_id = arg
            # Build URL for brand products
            url = f"https://m.aihuishou.com/n/#/category?brandId={brand_id}&cityId=1"
            print(f"[INFO] Using brand ID: {brand_id}")
        else:
            url = arg
        
        scraper = AihuishouScraper()
        result = await scraper.scrape(url)
        
        print_summary(result)
        
        if result.get("success"):
            export_data(result)
        else:
            print("\n[DEBUG] Raw responses captured:")
            for r in result.get("_debug", [])[:5]:
                print(f"  - {r.get('url')}")
                print(f"    Type: {r.get('data_type')}")
    
    else:
        print("\nUsage:")
        print("  python scraper.py [URL]")
        print("  python scraper.py [BRAND_ID]")
        print("\nExamples:")
        print("  python scraper.py \"https://m.aihuishou.com/n/#/inquiry?productId=43510\"")
        print("  python scraper.py \"https://m.aihuishou.com/n/#/category?frontCategoryId=6\"")
        print("  python scraper.py 52    # Apple products")
        print("  python scraper.py 9     # Huawei products")
        print("\nCommon Brand IDs:")
        print("  52  = Apple (苹果)      9   = Huawei (华为)")
        print("  184 = Xiaomi (小米)     7   = Samsung (三星)")
        print("  4   = OPPO              16  = vivo")
        print("  484 = Honor (荣耀)      357 = OnePlus (一加)")
        print("\nSupported URL types:")
        print("  - Product inquiry: /inquiry?productId=xxx")
        print("  - Category page:   /category?frontCategoryId=xxx")  
        print("  - Brand products:  /category?brandId=xxx")


if __name__ == "__main__":
    asyncio.run(main())

