"""
Aihuishou Category Scraper
Lay danh sach san pham tu category va xuat ra Excel/CSV

Usage:
    python scraper_category.py "URL_CATEGORY"
    
Example:
    python scraper_category.py "https://m.aihuishou.com/n/#/category?frontCategoryId=6"
"""

import re
import sys
import io
import json
import asyncio
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


async def get_category_products(url: str) -> Dict[str, Any]:
    """Lay danh sach san pham tu category page"""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            viewport={"width": 375, "height": 812},
            locale="zh-CN"
        )
        
        page = await context.new_page()
        
        # Storage for captured API responses
        captured_data = {
            "products": [],
            "brands": [],
            "categories": []
        }
        
        # Intercept API responses
        async def handle_response(response):
            url = response.url
            try:
                if "dubai.aihuishou.com" in url:
                    data = await response.json()
                    if data.get("code") == 0:
                        response_data = data.get("data")
                        
                        # Check if it's a product list (array with id, name, maxPrice)
                        if isinstance(response_data, list) and len(response_data) > 0:
                            first_item = response_data[0]
                            # Product items have id, name, maxPrice, imageUrl
                            if all(key in first_item for key in ["id", "name", "maxPrice"]):
                                captured_data["products"].extend(response_data)
                                print(f"[DEBUG] Captured {len(response_data)} products from: {url[:60]}...")
                            # Brand items have frontCategoryId, groups
                            elif "frontCategoryId" in first_item or "groups" in first_item:
                                print(f"[DEBUG] Skipped brand/category data")
                            else:
                                print(f"[DEBUG] Unknown list format with keys: {list(first_item.keys())[:5]}")
                        
                        # Check if it's brands response
                        elif isinstance(response_data, dict) and response_data.get("brands"):
                            captured_data["brands"] = response_data["brands"]
                            print(f"[DEBUG] Captured {len(response_data['brands'])} brands")
            except Exception as e:
                pass
        
        page.on("response", handle_response)
        
        try:
            # Set city cookie
            await context.add_cookies([{
                "name": "chosenCity",
                "value": "%7B%22id%22%3A1%2C%22name%22%3A%22%E4%B8%8A%E6%B5%B7%E5%B8%82%22%7D",
                "domain": "m.aihuishou.com",
                "path": "/"
            }])
            
            print(f"[INFO] Navigating to: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Try to click on first brand to get products
            print("[INFO] Looking for brand to click...")
            try:
                # Click on first visible brand (like Apple/苹果)
                brand_clicked = await page.evaluate("""
                    () => {
                        // Look for brand items in the list
                        const brandItems = document.querySelectorAll('[class*="brand"], [class*="Brand"], li, a');
                        for (const item of brandItems) {
                            const text = item.textContent;
                            // Look for Apple or first item with brand name
                            if (text.includes('苹果') || text.includes('Apple')) {
                                item.click();
                                return 'clicked Apple';
                            }
                        }
                        // Click first clickable item if no Apple found
                        const firstItem = document.querySelector('[class*="item"], [class*="brand"]');
                        if (firstItem) {
                            firstItem.click();
                            return 'clicked first item';
                        }
                        return 'no brand found';
                    }
                """)
                print(f"[DEBUG] {brand_clicked}")
                await asyncio.sleep(3)
            except Exception as e:
                print(f"[DEBUG] Brand click failed: {e}")
            
            # Scroll to load more products
            for i in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                print(f"[DEBUG] Scroll {i+1}/3... ({len(captured_data['products'])} products so far)")
            
            # Return captured data
            return {
                "success": True,
                "products": captured_data["products"],
                "brands": captured_data["brands"],
                "total_products": len(captured_data["products"])
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            await browser.close()


def export_to_excel(products: List[Dict], filename: str = None) -> str:
    """Export products to Excel file"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"aihuishou_products_{timestamp}.xlsx"
    
    # Prepare data for DataFrame
    data = []
    for p in products:
        data.append({
            "ID": p.get("id"),
            "Name": p.get("name"),
            "Brand ID": p.get("brandId"),
            "Category ID": p.get("categoryId"),
            "Max Price (CNY)": p.get("maxPrice"),
            "Image URL": p.get("imageUrl"),
            "Biz Type": p.get("bizType"),
            "Is Environmental Recycling": p.get("isEnvironmentalRecycling", False)
        })
    
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"[SUCCESS] Exported {len(data)} products to {filename}")
    return filename


def export_to_csv(products: List[Dict], filename: str = None) -> str:
    """Export products to CSV file"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"aihuishou_products_{timestamp}.csv"
    
    data = []
    for p in products:
        data.append({
            "ID": p.get("id"),
            "Name": p.get("name"),
            "Brand ID": p.get("brandId"),
            "Category ID": p.get("categoryId"),
            "Max Price (CNY)": p.get("maxPrice"),
            "Image URL": p.get("imageUrl"),
            "Biz Type": p.get("bizType"),
            "Is Environmental Recycling": p.get("isEnvironmentalRecycling", False)
        })
    
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"[SUCCESS] Exported {len(data)} products to {filename}")
    return filename


def print_products(products: List[Dict]):
    """Print products table to console"""
    print("\n" + "=" * 80)
    print(f"{'ID':<10} {'Name':<35} {'Max Price':>12} {'Brand ID':>10}")
    print("=" * 80)
    
    for p in products[:20]:  # Show first 20
        name = p.get("name", "N/A")[:33]
        print(f"{p.get('id', 'N/A'):<10} {name:<35} {p.get('maxPrice', 0):>10} CNY {p.get('brandId', 'N/A'):>8}")
    
    if len(products) > 20:
        print(f"... and {len(products) - 20} more products")
    
    print("=" * 80)


async def main():
    if len(sys.argv) > 1:
        url = sys.argv[1]
        
        print("=" * 60)
        print("  AIHUISHOU CATEGORY SCRAPER")
        print("=" * 60)
        
        result = await get_category_products(url)
        
        if result.get("success"):
            products = result.get("products", [])
            print(f"\n[SUCCESS] Found {len(products)} products")
            
            if products:
                print_products(products)
                
                # Export options
                print("\n[EXPORT] Exporting data...")
                try:
                    excel_file = export_to_excel(products)
                    csv_file = export_to_csv(products)
                    print(f"\n[FILES]")
                    print(f"  - Excel: {excel_file}")
                    print(f"  - CSV: {csv_file}")
                except Exception as e:
                    print(f"[WARNING] Excel export failed: {e}")
                    csv_file = export_to_csv(products)
                    print(f"  - CSV: {csv_file}")
                
                # Save JSON
                json_file = f"aihuishou_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(products, f, ensure_ascii=False, indent=2)
                print(f"  - JSON: {json_file}")
        else:
            print(f"[ERROR] {result.get('error', 'Unknown error')}")
    
    else:
        print("=" * 60)
        print("  AIHUISHOU CATEGORY SCRAPER")
        print("  Usage: python scraper_category.py [URL]")
        print("=" * 60)
        print("\nExample URLs:")
        print("  - Phones: https://m.aihuishou.com/n/#/category?frontCategoryId=6")
        print("  - Watches: https://m.aihuishou.com/n/#/category?frontCategoryId=144&subFrontCategoryId=145")
        print("\nThe scraper will export data to Excel, CSV, and JSON files.")


if __name__ == "__main__":
    asyncio.run(main())
