"""
AIHUISHOU DIRECT API SCRAPER
Crawl data directly from API - no browser automation

Usage:
    python direct_scraper.py
"""

import sys
import io
import requests
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class DirectScraper:
    """Scraper calls Aihuishou API directly"""
    
    BASE_URL = "https://dubai.aihuishou.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://m.aihuishou.com",
            "Referer": "https://m.aihuishou.com/",
            "Connection": "keep-alive",
        })
        # Add cookies
        self.session.cookies.set("chosenCity", "%7B%22id%22%3A1%2C%22name%22%3A%22%E4%B8%8A%E6%B5%B7%E5%B8%82%22%7D", domain="m.aihuishou.com")
    
    # ============ CATEGORY ============
    def get_categories(self) -> List[Dict]:
        """Get all categories"""
        url = f"{self.BASE_URL}/trade-front/api/inquiry/front-category/list"
        
        try:
            resp = self.session.get(url, timeout=10)
            print(f"  [DEBUG] Status: {resp.status_code}, Length: {len(resp.text)}")
            if resp.status_code != 200:
                print(f"  [DEBUG] Response: {resp.text[:200]}")
                return []
            data = resp.json()
            if data.get("code") == 0:
                categories = data.get("data", [])
                print(f"[OK] Found {len(categories)} categories")
                return categories
            else:
                print(f"  [DEBUG] API code: {data.get('code')}, msg: {data.get('msg')}")
        except Exception as e:
            print(f"[ERROR] get_categories: {e}")
        
        return []
    
    # ============ BRANDS ============
    def get_brands(self, category_id: int) -> List[Dict]:
        """Get brands by category"""
        url = f"{self.BASE_URL}/trade-front/api/trade/brand/list"
        params = {"frontCategoryId": category_id}
        
        try:
            resp = self.session.get(url, params=params, timeout=10)
            print(f"  [DEBUG] Status: {resp.status_code}, Length: {len(resp.text)}")
            if resp.status_code != 200:
                print(f"  [DEBUG] Response: {resp.text[:200]}")
                return []
            data = resp.json()
            if data.get("code") == 0:
                brands = data.get("data", [])
                print(f"[OK] Found {len(brands)} brands for category {category_id}")
                return brands
            else:
                print(f"  [DEBUG] API code: {data.get('code')}, msg: {data.get('msg')}")
        except Exception as e:
            print(f"[ERROR] get_brands: {e}")
        
        return []
    
    # ============ PRODUCTS (MODELS) ============
    def get_products(self, brand_id: int, category_id: Optional[int] = None, page: int = 1, size: int = 50) -> List[Dict]:
        """Lấy danh sách products/models theo brand"""
        url = f"{self.BASE_URL}/trade-front/api/trade/product/list"
        params = {
            "brandId": brand_id,
            "pageNo": page,
            "pageSize": size,
        }
        if category_id:
            params["frontCategoryId"] = category_id
        
        try:
            resp = self.session.get(url, params=params)
            data = resp.json()
            if data.get("code") == 0:
                products = data.get("data", [])
                print(f"[OK] Found {len(products)} products for brand {brand_id}")
                return products
        except Exception as e:
            print(f"[ERROR] get_products: {e}")
        
        return []
    
    def get_all_products(self, brand_id: int, category_id: Optional[int] = None, max_pages: int = 10) -> List[Dict]:
        """Lấy tất cả products với pagination"""
        all_products = []
        
        for page in range(1, max_pages + 1):
            products = self.get_products(brand_id, category_id, page)
            if not products:
                break
            all_products.extend(products)
            print(f"  Page {page}: {len(products)} products (total: {len(all_products)})")
        
        return all_products
    
    # ============ PRODUCT INQUIRY (Chi tiết sản phẩm) ============
    def get_product_inquiry(self, product_id: int) -> Optional[Dict]:
        """Lấy thông tin chi tiết sản phẩm (inquiry)"""
        url = f"{self.BASE_URL}/trade-front/api/inquiry/product/info"
        params = {"productId": product_id}
        
        try:
            resp = self.session.get(url, params=params)
            data = resp.json()
            if data.get("code") == 0:
                return data.get("data")
        except Exception as e:
            print(f"[ERROR] get_product_inquiry: {e}")
        
        return None
    
    # ============ CRAWL ALL ============
    def crawl_category(self, category_id: int) -> Dict[str, Any]:
        """Crawl toàn bộ data của 1 category"""
        result = {
            "category_id": category_id,
            "brands": [],
            "products": [],
        }
        
        # Lấy brands
        brands = self.get_brands(category_id)
        result["brands"] = brands
        
        # Lấy products cho từng brand
        for brand in brands:
            brand_id = brand.get("id")
            brand_name = brand.get("name", "Unknown")
            print(f"\n[BRAND] {brand_name} (ID: {brand_id})")
            
            products = self.get_all_products(brand_id, category_id)
            for p in products:
                p["brand_name"] = brand_name
            result["products"].extend(products)
        
        return result
    
    # ============ EXPORT ============
    def export_to_excel(self, products: List[Dict], filename: str = None):
        """Export products ra Excel"""
        if not products:
            print("[WARN] No products to export")
            return
        
        if not filename:
            filename = f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        df = pd.DataFrame([{
            "ID": p.get("id"),
            "Name": p.get("name"),
            "Brand": p.get("brand_name", p.get("brandId")),
            "Max Price": p.get("maxPrice"),
            "Image": p.get("imageUrl"),
        } for p in products])
        
        df.to_excel(filename, index=False)
        print(f"[EXPORTED] {len(products)} products -> {filename}")
        return filename
    
    def export_to_csv(self, products: List[Dict], filename: str = None):
        """Export products ra CSV"""
        if not products:
            print("[WARN] No products to export")
            return
        
        if not filename:
            filename = f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        df = pd.DataFrame([{
            "ID": p.get("id"),
            "Name": p.get("name"),
            "Brand": p.get("brand_name", p.get("brandId")),
            "Max Price": p.get("maxPrice"),
            "Image": p.get("imageUrl"),
        } for p in products])
        
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"[EXPORTED] {len(products)} products -> {filename}")
        return filename
    
    def export_to_json(self, data: Any, filename: str = None):
        """Export data ra JSON"""
        if not filename:
            filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"[EXPORTED] -> {filename}")
        return filename


# ============ MAIN ============
def main():
    print("=" * 60)
    print("  AIHUISHOU DIRECT API SCRAPER")
    print("  Crawl directly from API - No browser")
    print("=" * 60)
    
    scraper = DirectScraper()
    
    # 1. Lấy categories
    print("\n[STEP 1] Fetching categories...")
    categories = scraper.get_categories()
    for cat in categories[:10]:
        print(f"  {cat.get('id'):>3} - {cat.get('name')}")
    
    # 2. Lấy brands cho category Phones (ID=6)
    print("\n[STEP 2] Fetching brands for Phones (category 6)...")
    brands = scraper.get_brands(6)
    for b in brands[:10]:
        print(f"  {b.get('id'):>5} - {b.get('name')}")
    
    # 3. Lấy products cho Apple (brand ID thường là 1 hoặc tìm trong brands)
    apple_brand = next((b for b in brands if "苹果" in b.get("name", "") or "Apple" in b.get("name", "")), None)
    if apple_brand:
        brand_id = apple_brand.get("id")
        print(f"\n[STEP 3] Fetching products for {apple_brand.get('name')} (ID: {brand_id})...")
        products = scraper.get_all_products(brand_id, category_id=6, max_pages=3)
        
        print(f"\n[RESULT] Total products: {len(products)}")
        for p in products[:10]:
            print(f"  {p.get('id'):>8} | {p.get('name', 'N/A')[:40]:<42} | {p.get('maxPrice', 0):>6} CNY")
        
        # Export
        if products:
            print("\n[EXPORT]")
            scraper.export_to_excel(products)
            scraper.export_to_csv(products)
            scraper.export_to_json(products, f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    else:
        print("[WARN] Apple brand not found in brands list")
    
    print("\n" + "=" * 60)
    print("  DONE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
