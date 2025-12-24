"""
Aihuishou Product Scraper
Nhap link san pham de lay thong tin chi tiet va gia dinh gia.

Usage:
    python aihuishou_scraper.py [URL]
    
Example:
    python aihuishou_scraper.py "https://m.aihuishou.com/n/#/inquiry?productId=43510"
"""

import re
import sys
import json
import io
import requests
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any
from config import BASE_URL, DEFAULT_CITY_ID, HEADERS

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class AihuishouScraper:
    """Scraper de lay thong tin san pham tu m.aihuishou.com"""
    
    def __init__(self, city_id: int = DEFAULT_CITY_ID, city_name: str = "上海市"):
        self.city_id = city_id
        self.city_name = city_name
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.headers["x-city-id"] = str(city_id)
        
        # Import and set cookies
        from config import get_cookies
        self.session.cookies.update(get_cookies(city_id, city_name))
    
    def extract_product_id(self, url: str) -> Optional[int]:
        """Trích xuất productId từ URL"""
        # Pattern 1: /inquiry?productId=xxx
        if "productId=" in url:
            match = re.search(r'productId=(\d+)', url)
            if match:
                return int(match.group(1))
        
        # Pattern 2: /product/xxx
        match = re.search(r'/product/(\d+)', url)
        if match:
            return int(match.group(1))
        
        # Pattern 3: just a number
        if url.isdigit():
            return int(url)
        
        return None
    
    def get_product_detail(self, product_id: int) -> Dict[str, Any]:
        """Lấy thông tin chi tiết sản phẩm và câu hỏi định giá"""
        url = f"{BASE_URL}/recycle-products/quick-inquiry/{product_id}"
        params = {
            "cityId": self.city_id,
            "queryType": 1
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                return self._parse_product_data(data.get("data", {}))
            else:
                return {"error": data.get("resultMessage", "Unknown error")}
        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def _parse_product_data(self, data: Dict) -> Dict[str, Any]:
        """Parse và format dữ liệu sản phẩm"""
        product = data.get("product", {})
        ppvs = data.get("ppvs", [])  # Property-value pairs (câu hỏi định giá)
        
        result = {
            "id": product.get("id"),
            "name": product.get("name"),
            "brand": product.get("brandName"),
            "category": product.get("categoryName"),
            "imageUrl": product.get("imageUrl"),
            "maxPrice": product.get("maxPrice"),
            "minPrice": product.get("minPrice"),
            "questions": []
        }
        
        # Parse câu hỏi định giá
        for ppv in ppvs:
            question = {
                "name": ppv.get("propertyName"),
                "options": []
            }
            for value in ppv.get("propertyValues", []):
                question["options"].append({
                    "id": value.get("id"),
                    "name": value.get("valueName"),
                    "imageUrl": value.get("imageUrl")
                })
            result["questions"].append(question)
        
        return result
    
    def get_brands(self, category_id: int = 6) -> list:
        """Lấy danh sách brands theo category"""
        url = f"{BASE_URL}/front-category/brands-v2"
        payload = {
            "frontCategoryId": category_id,
            "cityId": self.city_id
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                brands = data.get("data", {}).get("brands", [])
                return [{"id": b.get("id"), "name": b.get("name")} for b in brands]
            return []
        except requests.RequestException:
            return []
    
    def search_products(self, brand_id: int, page: int = 0, page_size: int = 20) -> list:
        """Tìm sản phẩm theo brand"""
        url = f"{BASE_URL}/recycle-products/search-by-category"
        payload = {
            "brandId": brand_id,
            "cityId": self.city_id,
            "pageIndex": page,
            "pageSize": page_size
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                products = data.get("data", {}).get("products", [])
                return [{
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "maxPrice": p.get("maxPrice"),
                    "imageUrl": p.get("imageUrl")
                } for p in products]
            return []
        except requests.RequestException:
            return []
    
    def lookup(self, url_or_id: str) -> Dict[str, Any]:
        """
        Main lookup function - nhập URL hoặc product ID để tra cứu
        
        Args:
            url_or_id: URL hoặc product ID
            
        Returns:
            Dict chứa thông tin sản phẩm
        """
        product_id = self.extract_product_id(url_or_id)
        
        if product_id is None:
            return {"error": "Không thể trích xuất product ID từ URL"}
        
        return self.get_product_detail(product_id)


def print_product_info(data: Dict):
    """In thong tin san pham ra console"""
    if "error" in data:
        print(f"[ERROR] Loi: {data['error']}")
        return
    
    print("\n" + "="*60)
    print(f"[PRODUCT] {data.get('name', 'N/A')}")
    print("="*60)
    print(f"   ID:       {data.get('id')}")
    print(f"   Brand:    {data.get('brand')}")
    print(f"   Category: {data.get('category')}")
    print(f"   [PRICE]   {data.get('minPrice', 0)} - {data.get('maxPrice', 0)} CNY")
    print(f"   [IMAGE]   {data.get('imageUrl')}")
    
    if data.get("questions"):
        print("\n[QUESTIONS] Cau hoi dinh gia:")
        for q in data["questions"]:
            print(f"\n   > {q['name']}:")
            for opt in q["options"][:5]:  # Hien thi toi da 5 options
                print(f"      - {opt['name']} (ID: {opt['id']})")
            if len(q["options"]) > 5:
                print(f"      ... va {len(q['options']) - 5} options khac")
    
    print("\n" + "="*60)


def export_to_excel(data_list: list, filename: str = None):
    """Export data list to Excel"""
    import pandas as pd
    from datetime import datetime
    
    if not data_list:
        print("[WARN] No data to export")
        return None
    
    if not filename:
        filename = f"aihuishou_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    # Flatten data for Excel
    rows = []
    for item in data_list:
        row = {
            "ID": item.get("id"),
            "Name": item.get("name"),
            "Brand": item.get("brand") or item.get("brandName"),
            "Category": item.get("category") or item.get("categoryName"),
            "Max Price": item.get("maxPrice"),
            "Min Price": item.get("minPrice"),
            "Image URL": item.get("imageUrl"),
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    df.to_excel(filename, index=False)
    print(f"[EXPORT] Saved to {filename}")
    return filename


def export_to_csv(data_list: list, filename: str = None):
    """Export data list to CSV"""
    import pandas as pd
    from datetime import datetime
    
    if not data_list:
        print("[WARN] No data to export")
        return None
    
    if not filename:
        filename = f"aihuishou_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    rows = []
    for item in data_list:
        row = {
            "ID": item.get("id"),
            "Name": item.get("name"),
            "Brand": item.get("brand") or item.get("brandName"),
            "Category": item.get("category") or item.get("categoryName"),
            "Max Price": item.get("maxPrice"),
            "Min Price": item.get("minPrice"),
            "Image URL": item.get("imageUrl"),
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"[EXPORT] Saved to {filename}")
    return filename


def export_to_json(data: Any, filename: str = None):
    """Export data to JSON"""
    from datetime import datetime
    
    if not filename:
        filename = f"aihuishou_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"[EXPORT] Saved to {filename}")
    return filename


def main():
    import sys
    
    scraper = AihuishouScraper()
    
    # Check for --export flag
    export_format = None
    if "--xlsx" in sys.argv or "--excel" in sys.argv:
        export_format = "xlsx"
        sys.argv = [a for a in sys.argv if a not in ["--xlsx", "--excel"]]
    elif "--csv" in sys.argv:
        export_format = "csv"
        sys.argv = [a for a in sys.argv if a != "--csv"]
    elif "--json" in sys.argv:
        export_format = "json"
        sys.argv = [a for a in sys.argv if a != "--json"]
    
    if len(sys.argv) > 1:
        # Lay URL tu command line
        url = sys.argv[1]
        print(f"[SEARCH] Dang tra cuu: {url}")
        result = scraper.lookup(url)
        print_product_info(result)
        
        # Export if requested
        if export_format and "error" not in result:
            if export_format == "xlsx":
                export_to_excel([result])
            elif export_format == "csv":
                export_to_csv([result])
            elif export_format == "json":
                export_to_json(result)
        else:
            # Xuat JSON
            print("\n[JSON] JSON Output:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Interactive mode
        print("="*60)
        print("   AIHUISHOU PRODUCT LOOKUP")
        print("   Nhap link san pham de tra cuu thong tin")
        print("   Commands: --xlsx, --csv, --json de export")
        print("="*60)
        
        results = []
        while True:
            try:
                url = input("\n[INPUT] Nhap URL (hoac 'q' de thoat, 'export' de xuat file): ").strip()
                
                if url.lower() == 'q':
                    print("[BYE] Tam biet!")
                    break
                
                if url.lower() == 'export':
                    if results:
                        export_to_excel(results)
                        export_to_csv(results)
                        export_to_json(results)
                    else:
                        print("[WARN] Chua co du lieu de export")
                    continue
                
                if not url:
                    continue
                
                print(f"\n[SEARCH] Dang tra cuu...")
                result = scraper.lookup(url)
                print_product_info(result)
                
                if "error" not in result:
                    results.append(result)
                    print(f"[INFO] Da luu {len(results)} san pham. Nhap 'export' de xuat file.")
                
            except KeyboardInterrupt:
                print("\n[BYE] Tam biet!")
                break


if __name__ == "__main__":
    main()
