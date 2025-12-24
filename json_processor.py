"""
Aihuishou JSON Processor
Xu ly du lieu JSON da copy tu browser va xuat ra Excel

Usage:
    1. Mo browser, vao trang aihuishou category
    2. Mo Developer Tools (F12) -> Network tab  
    3. Copy response JSON tu API call
    4. Dan vao file input.json
    5. Chay: python json_processor.py input.json
"""

import sys
import io
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def process_json_file(filepath: str):
    """Process JSON file and export to Excel/CSV"""
    
    print("=" * 60)
    print("  AIHUISHOU JSON PROCESSOR")
    print("=" * 60)
    
    # Read JSON file
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different JSON structures
    products = []
    
    # If it's API response format: {"code": 0, "data": [...]}
    if isinstance(data, dict) and "code" in data:
        if data.get("code") == 0:
            products = data.get("data", [])
        else:
            print(f"[ERROR] API returned error: {data.get('resultMessage')}")
            return
    # If it's direct array
    elif isinstance(data, list):
        products = data
    else:
        print("[ERROR] Unknown JSON format")
        return
    
    if not products:
        print("[WARNING] No products found in JSON")
        return
    
    print(f"\n[INFO] Found {len(products)} items")
    
    # Detect item type and prepare DataFrame
    first_item = products[0]
    
    # Product structure
    if "maxPrice" in first_item:
        print("[INFO] Detected: Product list")
        rows = []
        for p in products:
            rows.append({
                "ID": p.get("id"),
                "Name": p.get("name"),
                "Max Price (CNY)": p.get("maxPrice"),
                "Brand ID": p.get("brandId"),
                "Category ID": p.get("categoryId"),
                "Image URL": p.get("imageUrl"),
                "Banner Image": p.get("bannerImageUrl"),
                "Biz Type": p.get("bizType"),
                "Type": p.get("type"),
                "Is Environmental Recycling": p.get("isEnvironmentalRecycling"),
                "Marketing Tag": p.get("marketingTagText")
            })
        df = pd.DataFrame(rows)
        
        # Print preview
        print("\n[PREVIEW] First 10 products:")
        print("-" * 70)
        for p in products[:10]:
            print(f"  {p.get('id'):<8} {p.get('name', 'N/A'):<35} {p.get('maxPrice', 0):>8} CNY")
        if len(products) > 10:
            print(f"  ... and {len(products) - 10} more")
        print("-" * 70)
    
    # Brand structure  
    elif "iconUrl" in first_item and "initial" in first_item:
        print("[INFO] Detected: Brand list")
        rows = []
        for b in products:
            rows.append({
                "ID": b.get("id"),
                "Name": b.get("name"),
                "Initial": b.get("initial"),
                "Icon URL": b.get("iconUrl"),
                "Marketing Tag": b.get("marketingTagText")
            })
        df = pd.DataFrame(rows)
    
    # Generic - just dump all keys
    else:
        print("[INFO] Detected: Generic list")
        df = pd.DataFrame(products)
    
    # Export
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(filepath).stem
    
    excel_file = f"{base_name}_{timestamp}.xlsx"
    csv_file = f"{base_name}_{timestamp}.csv"
    
    df.to_excel(excel_file, index=False, engine='openpyxl')
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    
    print(f"\n[SUCCESS] Exported {len(products)} items")
    print(f"  Excel: {excel_file}")
    print(f"  CSV:   {csv_file}")
    
    return df


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage: python json_processor.py <json_file>")
        print("\nExample:")
        print("  python json_processor.py products.json")
        print("\nThe JSON can be:")
        print('  - API response: {"code": 0, "data": [...]}')
        print('  - Direct array: [{"id": 1, ...}, ...]')
        return
    
    filepath = sys.argv[1]
    
    if not Path(filepath).exists():
        print(f"[ERROR] File not found: {filepath}")
        return
    
    process_json_file(filepath)


if __name__ == "__main__":
    main()
