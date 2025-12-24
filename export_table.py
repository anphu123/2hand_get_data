"""
DYNAMIC EXPORT DATA TO TABLE FORMAT
Tự động nhận diện cấu trúc JSON và xuất với cột phù hợp

Supported JSON types:
- deep_scrape: Brand → Series → Product (watches, bags, shoes)
- brand_list: Category → Brand list (phones, laptops)
- product_list: Brand → Model (product catalog)
- inquiry: Assessment data

Usage:
    python export_table.py input.json [output.csv]
"""

import sys
import io
import json
import csv
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple


def timer(func):
    """Decorator to measure function execution time"""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        print(f"  ⏱ {func.__name__}: {elapsed:.1f}ms")
        return result
    return wrapper

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ============ COLUMN CONFIGURATIONS ============
COLUMN_CONFIGS = {
    'deep_scrape': ['序号', '品牌Brand', '系列Series', '产品名Product', '规格Spec', '产品ID'],
    'brand_list': ['序号', '分类Category', '品牌Brand', 'Brand ID', 'Icon URL'],
    'product_list': ['序号', '品牌Brand', '型号Model', '最高价MaxPrice', '产品ID', '图片URL'],
    'category_brand': ['序号', 'frontCategoryId', '分组Group', '品牌Brand', 'Brand ID'],
    'unknown': ['序号', 'Key', 'Value']
}


def load_json(filepath: str) -> Any:
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def detect_json_type(data: Any) -> str:
    """
    Auto-detect JSON structure type
    Returns: 'deep_scrape', 'brand_list', 'product_list', 'category_brand', 'unknown'
    """
    if isinstance(data, list) and len(data) > 0:
        first = data[0]
        
        # Type 1: deep_scrape - has brand, series, productName, productId
        if isinstance(first, dict):
            if all(k in first for k in ['brand', 'series', 'productName', 'productId']):
                return 'deep_scrape'
            
            # Type 2: category_brand - has frontCategoryId, groups
            if 'frontCategoryId' in first and 'groups' in first:
                return 'category_brand'
            
            # Type 3: brand_list - has id, name, iconUrl (no productId)
            if 'id' in first and 'name' in first and 'iconUrl' in first and 'productId' not in first:
                return 'brand_list'
    
    # Type 4: product_list - dict with 'data' containing products
    if isinstance(data, dict) and 'data' in data:
        items = data.get('data', [])
        if isinstance(items, list) and len(items) > 0:
            first = items[0]
            if isinstance(first, dict) and 'id' in first and 'name' in first:
                if 'maxPrice' in first or 'categoryId' in first:
                    return 'product_list'
    
    # Type 5: brands in dict
    if isinstance(data, dict) and 'brands' in data:
        return 'brand_list'
    
    return 'unknown'


# ============ EXTRACTOR FUNCTIONS ============

def extract_deep_scrape(data: List[Dict]) -> List[Dict]:
    """Extract from deep scrape format (watches, bags, shoes)"""
    results = []
    for i, item in enumerate(data, 1):
        results.append({
            '序号': i,
            '品牌Brand': item.get('brand', ''),
            '系列Series': item.get('series', ''),
            '产品名Product': item.get('productName', ''),
            '规格Spec': item.get('subTitle', ''),
            '产品ID': item.get('productId', '')
        })
    return results


def extract_category_brand(data: List[Dict]) -> List[Dict]:
    """Extract from category-brand format (frontCategoryId + groups)"""
    results = []
    seq = 1
    
    for item in data:
        if not isinstance(item, dict):
            continue
            
        front_cat_id = item.get('frontCategoryId', '')
        
        for group in item.get('groups', []):
            group_name = group.get('groupName', '')
            
            for brand in group.get('details', []):
                results.append({
                    '序号': seq,
                    'frontCategoryId': front_cat_id,
                    '分组Group': group_name,
                    '品牌Brand': brand.get('name', ''),
                    'Brand ID': brand.get('id', '')
                })
                seq += 1
    
    return results


def extract_brand_list(data: Any) -> List[Dict]:
    """Extract from brand list format"""
    results = []
    seq = 1
    
    # Handle list of brands
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'id' in item and 'name' in item:
                results.append({
                    '序号': seq,
                    '分类Category': 'Brand',
                    '品牌Brand': item.get('name', ''),
                    'Brand ID': item.get('id', ''),
                    'Icon URL': item.get('iconUrl', '')
                })
                seq += 1
    
    # Handle dict with 'brands' key
    elif isinstance(data, dict) and 'brands' in data:
        for brand in data.get('brands', []):
            results.append({
                '序号': seq,
                '分类Category': 'Brand',
                '品牌Brand': brand.get('name', ''),
                'Brand ID': brand.get('id', ''),
                'Icon URL': brand.get('iconUrl', '')
            })
            seq += 1
    
    return results


def extract_product_list(data: Dict) -> List[Dict]:
    """Extract from product list format"""
    results = []
    items = data.get('data', [])
    
    for i, item in enumerate(items, 1):
        results.append({
            '序号': i,
            '品牌Brand': item.get('name', '').split(' ')[0] if item.get('name') else '',
            '型号Model': item.get('name', ''),
            '最高价MaxPrice': item.get('maxPrice', ''),
            '产品ID': item.get('id', ''),
            '图片URL': item.get('imageUrl', '')
        })
    
    return results


def extract_unknown(data: Any) -> List[Dict]:
    """Extract from unknown format - flatten to key-value pairs"""
    results = []
    
    if isinstance(data, dict):
        for i, (k, v) in enumerate(data.items(), 1):
            results.append({
                '序号': i,
                'Key': k,
                'Value': str(v)[:100]  # Truncate long values
            })
    
    return results


# ============ MAIN EXTRACT FUNCTION ============

def extract_data(data: Any) -> Tuple[str, List[Dict], List[str]]:
    """
    Auto-detect and extract data
    Returns: (json_type, extracted_data, column_names)
    """
    json_type = detect_json_type(data)
    
    extractors = {
        'deep_scrape': extract_deep_scrape,
        'category_brand': extract_category_brand,
        'brand_list': extract_brand_list,
        'product_list': extract_product_list,
        'unknown': extract_unknown
    }
    
    extractor = extractors.get(json_type, extract_unknown)
    results = extractor(data)
    columns = COLUMN_CONFIGS.get(json_type, COLUMN_CONFIGS['unknown'])
    
    return json_type, results, columns


# ============ EXPORT FUNCTIONS ============

def export_to_csv(data: List[Dict], columns: List[str], output_file: str = None):
    """Export to CSV file with dynamic columns"""
    if not output_file:
        output_file = f"table_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    if not data:
        print("No data to export!")
        return None
    
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
    
    print(f"[EXPORTED] {output_file}")
    return output_file


def export_to_txt(data: List[Dict], columns: List[str], output_file: str = None):
    """Export to TXT file with table format"""
    if not output_file:
        output_file = f"table_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    if not data:
        print("No data to export!")
        return None
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write(" | ".join(columns) + "\n")
        f.write("-" * 100 + "\n")
        
        # Data rows
        for row in data:
            values = [str(row.get(col, '')) for col in columns]
            f.write(" | ".join(values) + "\n")
    
    print(f"[EXPORTED] {output_file}")
    return output_file


def print_table(data: List[Dict], columns: List[str], limit: int = 20):
    """Print table to console"""
    print("\n" + "=" * 100)
    print(" | ".join(columns))
    print("-" * 100)
    
    for i, row in enumerate(data):
        if i >= limit:
            print(f"... and {len(data) - limit} more rows")
            break
        values = [str(row.get(col, ''))[:30] for col in columns]  # Truncate long values
        print(" | ".join(values))
    
    print("=" * 100)
    print(f"Total: {len(data)} rows")


# ============ MAIN ============

def main():
    total_start = time.perf_counter()
    
    # Default to newest JSON file if no argument provided
    if len(sys.argv) < 2:
        import glob
        json_files = glob.glob("*.json")
        if not json_files:
            print("Usage: python export_table.py input.json [output.csv]")
            print("No JSON files found in current directory!")
            return
        
        # Use the largest file (faster sort by file size from os.stat)
        import os
        json_files.sort(key=lambda x: -os.path.getsize(x))
        input_file = json_files[0]
        print(f"Using: {input_file}")
    else:
        input_file = sys.argv[1]
    
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Load JSON with timing
    print(f"\n[LOADING] {input_file}")
    t1 = time.perf_counter()
    data = load_json(input_file)
    print(f"  ⏱ load_json: {(time.perf_counter() - t1) * 1000:.1f}ms")
    
    # Detect and extract with timing
    print("[PROCESSING]")
    t2 = time.perf_counter()
    json_type, results, columns = extract_data(data)
    print(f"  ⏱ detect+extract: {(time.perf_counter() - t2) * 1000:.1f}ms")
    
    print(f"[DETECTED] Type: {json_type}")
    print(f"[COLUMNS] {', '.join(columns)}")
    
    if results:
        # Print preview (skip if large dataset for speed)
        if len(results) <= 100:
            print_table(results, columns)
        else:
            print(f"\n[PREVIEW] {len(results)} rows (skipped preview for speed)")
        
        # Export with timing
        print("\n[EXPORTING]")
        t3 = time.perf_counter()
        csv_file = export_to_csv(results, columns, output_file)
        print(f"  ⏱ export_csv: {(time.perf_counter() - t3) * 1000:.1f}ms")
        
        t4 = time.perf_counter()
        txt_file = output_file.replace('.csv', '.txt') if output_file else None
        export_to_txt(results, columns, txt_file)
        print(f"  ⏱ export_txt: {(time.perf_counter() - t4) * 1000:.1f}ms")
        
        # Total time
        total_time = (time.perf_counter() - total_start) * 1000
        print(f"\n{'='*50}")
        print(f"✅ DONE: {len(results)} rows in {total_time:.0f}ms")
        print(f"   Speed: {len(results) / (total_time/1000):.0f} rows/sec")
        print(f"{'='*50}")
    else:
        print("[WARNING] No data extracted! Check JSON structure.")


if __name__ == "__main__":
    main()

