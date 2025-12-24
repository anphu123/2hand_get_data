"""
Aihuishou Product Scraper - Browser Automation Version (Improved)
Su dung Playwright de lay thong tin san pham tu m.aihuishou.com

Usage:
    python scraper_browser.py [URL]
    
Example:
    python scraper_browser.py "https://m.aihuishou.com/n/#/inquiry?productId=43510"
"""

import re
import sys
import io
import json
import asyncio
from typing import Optional, Dict, Any

# Fix Windows console encoding for Chinese characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


async def get_product_data(url: str) -> Dict[str, Any]:
    """Lay thong tin san pham bang Playwright"""
    from playwright.async_api import async_playwright
    
    # Extract productId from URL
    match = re.search(r'productId=(\d+)', url)
    if not match:
        return {"error": "Cannot extract productId from URL"}
    
    product_id = match.group(1)
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            viewport={"width": 375, "height": 812},
            locale="zh-CN"
        )
        
        page = await context.new_page()
        
        # Storage for captured API response
        api_data = {}
        
        # Intercept API responses
        async def handle_response(response):
            url = response.url
            if "quick-inquiry" in url or "recycle-products" in url:
                try:
                    data = await response.json()
                    if data.get("code") == 0:
                        api_data["response"] = data
                        print(f"[DEBUG] Captured API response from: {url[:80]}...")
                except Exception as e:
                    print(f"[DEBUG] Failed to parse response: {e}")
        
        page.on("response", handle_response)
        
        try:
            # Set city cookie first
            await context.add_cookies([{
                "name": "chosenCity",
                "value": "%7B%22id%22%3A1%2C%22name%22%3A%22%E4%B8%8A%E6%B5%B7%E5%B8%82%22%7D",
                "domain": "m.aihuishou.com",
                "path": "/"
            }])
            
            print("[DEBUG] Navigating to page...")
            
            # Go to product page
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for network to settle
            print("[DEBUG] Waiting for network...")
            await asyncio.sleep(5)
            
            # Check if we captured API data
            if api_data.get("response"):
                print("[DEBUG] Found API response!")
                data = api_data["response"]
                # Debug: print raw response to understand structure
                print(f"[DEBUG] Raw response keys: {list(data.keys())}")
                if data.get("data"):
                    print(f"[DEBUG] Data keys: {list(data['data'].keys())}")
                    # Save raw response for debugging
                    with open("debug_response.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print("[DEBUG] Raw response saved to debug_response.json")
                return parse_product_data(data.get("data", {}))
            
            # If no API data, try to scrape from page
            print("[DEBUG] No API response, trying to scrape page...")
            
            # Take screenshot for debugging
            await page.screenshot(path="debug_screenshot.png")
            print("[DEBUG] Screenshot saved to debug_screenshot.png")
            
            # Get page content for debugging
            content = await page.content()
            print(f"[DEBUG] Page length: {len(content)} chars")
            
            # Try to extract data from page
            result = await scrape_page_content(page)
            return result
            
        except Exception as e:
            return {"error": f"Browser error: {str(e)}"}
        finally:
            await browser.close()


async def scrape_page_content(page) -> Dict[str, Any]:
    """Scrape product info directly from page DOM"""
    try:
        # Wait a bit more for dynamic content
        await asyncio.sleep(2)
        
        # Extract data using JavaScript
        data = await page.evaluate("""
            () => {
                const result = {
                    name: null,
                    maxPrice: null,
                    questions: [],
                    debug: {}
                };
                
                // Get all text content for debugging
                result.debug.bodyText = document.body ? document.body.innerText.substring(0, 500) : 'no body';
                
                // Try multiple selectors for product name
                const nameSelectors = [
                    '.product-name',
                    '.inquiry-title', 
                    '.product-info h1',
                    '.product-title',
                    '[class*="product"] [class*="name"]',
                    '[class*="title"]',
                    'h1',
                    'h2'
                ];
                
                for (const sel of nameSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.textContent.trim()) {
                        result.name = el.textContent.trim();
                        result.debug.nameSelector = sel;
                        break;
                    }
                }
                
                // Get max price with multiple selectors
                const priceSelectors = [
                    '.max-price',
                    '.price-value',
                    '[class*="price"]',
                    '[class*="Price"]'
                ];
                
                for (const sel of priceSelectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const priceText = el.textContent;
                        const priceMatch = priceText.match(/\\d+/);
                        if (priceMatch) {
                            result.maxPrice = parseInt(priceMatch[0]);
                            result.debug.priceSelector = sel;
                            break;
                        }
                    }
                }
                
                return result;
            }
        """)
        
        print(f"[DEBUG] Scraped data: {json.dumps(data.get('debug', {}), ensure_ascii=False)}")
        
        if data.get("name"):
            del data["debug"]
            return data
        else:
            return {"error": "Could not find product data on page", "debug": data.get("debug", {})}
            
    except Exception as e:
        return {"error": f"Scrape error: {str(e)}"}


def parse_product_data(data: Dict) -> Dict[str, Any]:
    """Parse API response data - updated to match actual API structure"""
    # New structure uses productName, productId, couponPrice directly in data
    # Questions are in quickInquiry.items
    
    quick_inquiry = data.get("quickInquiry", {})
    items = quick_inquiry.get("items", [])
    
    result = {
        "id": data.get("productId"),
        "name": data.get("productName"),
        "couponPrice": data.get("couponPrice"),
        "templateType": data.get("templateType"),
        "questions": []
    }
    
    # Parse quickInquiry items as questions
    for item in items:
        question = {
            "id": item.get("id"),
            "name": item.get("name"),
            "description": item.get("description"),
            "value": item.get("value"),
            "isNoAdditional": item.get("isNoAdditional"),
            "noAdditionalTips": item.get("noAdditionalTips"),
            "options": []
        }
        
        # Get ppvs (property-value pairs) as options
        for ppv in item.get("ppvs", []):
            question["options"].append({
                "id": ppv.get("id"),
                "name": ppv.get("name"),
                "tags": ppv.get("tags", [])
            })
        
        result["questions"].append(question)
    
    return result


def print_product_info(data: Dict):
    """Print product info to console"""
    if "error" in data:
        print(f"[ERROR] {data['error']}")
        if data.get("debug"):
            print(f"[DEBUG INFO] {data['debug']}")
        return
    
    print("\n" + "="*60)
    print(f"[PRODUCT] {data.get('name', 'N/A')}")
    print("="*60)
    print(f"   ID:           {data.get('id', 'N/A')}")
    print(f"   Coupon Price: {data.get('couponPrice', 0)} CNY")
    
    if data.get("questions"):
        print(f"\n[QUESTIONS] Valuation Questions ({len(data['questions'])} items):")
        for q in data["questions"]:
            status = ""
            if q.get("isNoAdditional"):
                status = f" [{q.get('noAdditionalTips', 'N/A')}]"
            print(f"\n   > {q['name']}{status}")
            if q.get("description"):
                print(f"     Desc: {q['description'][:50]}...")
            
            # Show first 3 options
            for opt in q["options"][:3]:
                tags = ""
                if opt.get("tags"):
                    tag_names = [t.get("name", "") for t in opt["tags"]]
                    tags = f" [{', '.join(tag_names)}]"
                print(f"        - {opt['name']}{tags}")
            if len(q["options"]) > 3:
                print(f"        ... and {len(q['options']) - 3} more options")
    
    print("\n" + "="*60)


async def main():
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"[SEARCH] Looking up: {url}")
        result = await get_product_data(url)
        print_product_info(result)
        
        print("\n[JSON] JSON Output:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("="*60)
        print("   AIHUISHOU PRODUCT LOOKUP (Browser Mode)")
        print("   Enter product link to get info")
        print("="*60)
        
        while True:
            try:
                url = input("\n[INPUT] Enter URL (or 'q' to quit): ").strip()
                
                if url.lower() == 'q':
                    print("[BYE] Goodbye!")
                    break
                
                if not url:
                    continue
                
                print(f"\n[SEARCH] Looking up...")
                result = await get_product_data(url)
                print_product_info(result)
                
            except KeyboardInterrupt:
                print("\n[BYE] Goodbye!")
                break


if __name__ == "__main__":
    asyncio.run(main())
