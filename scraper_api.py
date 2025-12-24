"""
Aihuishou API Scraper
Truc tiep goi API de lay danh sach san pham

Usage:
    python scraper_api.py [BRAND_ID] [CATEGORY_ID]
    
Example:
    python scraper_api.py 52 1       # Apple phones
    python scraper_api.py 9 1        # Huawei phones
"""

import sys
import io
import json
import asyncio
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# API Configuration
BASE_URL = "https://dubai.aihuishou.com/dubai-gateway"
DEFAULT_CITY_ID = 1  # Shanghai


async def get_session_cookies():
    """Get cookies from browser session"""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
            viewport={"width": 375, "height": 812}
        )
        page = await context.new_page()
        
        # Navigate to set cookies
        await page.goto("https://m.aihuishou.com/n/#/", timeout=30000)
        await asyncio.sleep(2)
        
        cookies = await context.cookies()
        await browser.close()
        
        return {c["name"]: c["value"] for c in cookies}


async def search_products(brand_id: int, city_id: int = 1, page_index: int = 0, page_size: int = 50) -> Dict:
    """Search products by brand using direct API call"""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
            viewport={"width": 375, "height": 812}
        )
        page = await context.new_page()
        
        # Set city cookie
        await context.add_cookies([{
            "name": "chosenCity",
            "value": "%7B%22id%22%3A1%2C%22name%22%3A%22%E4%B8%8A%E6%B5%B7%E5%B8%82%22%7D",
            "domain": "m.aihuishou.com",
            "path": "/"
        }])
        
        products = []
        
        # Intercept responses
        async def handle_response(response):
            if "recycle-products" in response.url:
                try:
                    data = await response.json()
                    if data.get("code") == 0 and isinstance(data.get("data"), list):
                        first = data["data"][0] if data["data"] else {}
                        if "maxPrice" in first:
                            products.extend(data["data"])
                            print(f"[DEBUG] Got {len(data['data'])} products")
                except:
                    pass
        
        page.on("response", handle_response)
        
        # Navigate to brand page which triggers the product search API
        url = f"https://m.aihuishou.com/n/#/category?brandId={brand_id}&cityId={city_id}"
        print(f"[INFO] Navigating to: {url}")
        await page.goto(url, timeout=30000)
        await asyncio.sleep(5)
        
        # Scroll to load more
        for i in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
        
        await browser.close()
        return {"products": products, "total": len(products)}


async def get_brands(front_category_id: int = 6) -> List[Dict]:
    """Get list of brands for a category"""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
            viewport={"width": 375, "height": 812}
        )
        page = await context.new_page()
        
        brands = []
        
        async def handle_response(response):
            if "dubai.aihuishou.com" in response.url:
                try:
                    data = await response.json()
                    if data.get("code") == 0:
                        resp_data = data.get("data")
                        if isinstance(resp_data, list) and len(resp_data) > 0:
                            first = resp_data[0]
                            if "initial" in first and "iconUrl" in first:
                                brands.extend(resp_data)
                                print(f"[DEBUG] Got {len(resp_data)} brands")
                except:
                    pass
        
        page.on("response", handle_response)
        
        url = f"https://m.aihuishou.com/n/#/category?frontCategoryId={front_category_id}"
        await page.goto(url, timeout=30000)
        await asyncio.sleep(3)
        
        await browser.close()
        return brands


def export_products(products: List[Dict], prefix: str = "products"):
    """Export products to Excel/CSV/JSON"""
    if not products:
        print("[WARNING] No products to export")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Prepare DataFrame
    data = []
    for p in products:
        data.append({
            "ID": p.get("id"),
            "Name": p.get("name"),
            "Max Price (CNY)": p.get("maxPrice"),
            "Brand ID": p.get("brandId"),
            "Category ID": p.get("categoryId"),
            "Image URL": p.get("imageUrl"),
            "Biz Type": p.get("bizType"),
            "Type": p.get("type"),
            "Is Environmental Recycling": p.get("isEnvironmentalRecycling")
        })
    
    df = pd.DataFrame(data)
    
    # Export files
    excel_file = f"{prefix}_{timestamp}.xlsx"
    csv_file = f"{prefix}_{timestamp}.csv"
    json_file = f"{prefix}_{timestamp}.json"
    
    df.to_excel(excel_file, index=False, engine='openpyxl')
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    print(f"\n[EXPORTED]")
    print(f"  Excel: {excel_file}")
    print(f"  CSV:   {csv_file}")
    print(f"  JSON:  {json_file}")
    
    return excel_file, csv_file, json_file


def print_products_table(products: List[Dict]):
    """Pretty print products"""
    print("\n" + "=" * 85)
    print(f"{'ID':<10} {'Name':<40} {'Max Price':>12} {'BrandID':>8}")
    print("=" * 85)
    
    for p in products[:30]:
        name = str(p.get("name", "N/A"))[:38]
        print(f"{p.get('id', 'N/A'):<10} {name:<40} {p.get('maxPrice', 0):>10} CNY {p.get('brandId', 'N/A'):>6}")
    
    if len(products) > 30:
        print(f"... and {len(products) - 30} more")
    print("=" * 85)


async def main():
    print("=" * 60)
    print("  AIHUISHOU API SCRAPER")
    print("=" * 60)
    
    if len(sys.argv) >= 2:
        brand_id = int(sys.argv[1])
        city_id = int(sys.argv[2]) if len(sys.argv) >= 3 else 1
        
        print(f"\n[SEARCH] Brand ID: {brand_id}, City ID: {city_id}")
        result = await search_products(brand_id, city_id)
        
        if result["products"]:
            print(f"\n[SUCCESS] Found {result['total']} products")
            print_products_table(result["products"])
            export_products(result["products"], f"brand_{brand_id}")
        else:
            print("[WARNING] No products found")
    else:
        print("\nUsage:")
        print("  python scraper_api.py [BRAND_ID] [CITY_ID]")
        print("\nCommon Brand IDs:")
        print("  52  = Apple (苹果)")
        print("  9   = Huawei (华为)")
        print("  184 = Xiaomi (小米)")
        print("  7   = Samsung (三星)")
        print("  4   = OPPO")
        print("  16  = vivo")
        print("\nExample:")
        print("  python scraper_api.py 52 1  # Get all Apple products")
        
        print("\n[INFO] Getting brands for phones (frontCategoryId=6)...")
        brands = await get_brands(6)
        
        if brands:
            print(f"\n[BRANDS] Found {len(brands)} brands:")
            for b in brands[:15]:
                print(f"  {b.get('id'):<6} {b.get('name')}")
            if len(brands) > 15:
                print(f"  ... and {len(brands) - 15} more")


if __name__ == "__main__":
    asyncio.run(main())
