"""
EXPORT DATA TO TABLE FORMAT
Xuất dữ liệu theo định dạng bảng đơn giản

Output format:
序号 | 品牌brand | 系列类型Series type
1 | Audemars Piguet/爱彼 | CODE 11.59 瑞表 蓝色 26439NB.OO.A346KB.01

Usage:
    python export_table.py input.json [output.csv]
"""

import sys
import io
import json
import csv
from datetime import datetime
from typing import List, Dict, Any

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def load_json(filepath: str) -> Any:
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_brands_and_series(data: Any) -> List[Dict]:
    """
    Extract brands and series from JSON data
    Returns list of: [序号, 品牌brand, 系列类型Series type]
    """
    results = []
    seq = 1  # 序号
    
    # Try to find brand data in different structures
    if isinstance(data, list):
        for item in data:
            # Check if item is a category with brands
            if isinstance(item, dict):
                # Structure 1: {frontCategoryId, groups: [{groupName, details}]}
                if 'groups' in item and 'frontCategoryId' in item:
                    for group in item.get('groups', []):
                        for brand in group.get('details', []):
                            results.append({
                                '序号': seq,
                                '品牌brand': brand.get('name', ''),
                                '系列类型Series type': f"{group.get('groupName', '')} - ID:{brand.get('id', '')}"
                            })
                            seq += 1
                
                # Structure 2: Direct brand list with id, name, iconUrl
                elif 'id' in item and 'name' in item and 'iconUrl' in item:
                    results.append({
                        '序号': seq,
                        '品牌brand': item.get('name', ''),
                        '系列类型Series type': f"Brand ID: {item.get('id', '')}"
                    })
                    seq += 1
                
                # Structure 3: Nested list or complex structure
                elif isinstance(item, list):
                    for sub_item in item:
                        if isinstance(sub_item, dict) and 'frontCategoryId' in sub_item:
                            for group in sub_item.get('groups', []):
                                for brand in group.get('details', []):
                                    results.append({
                                        '序号': seq,
                                        '品牌brand': brand.get('name', ''),
                                        '系列类型Series type': f"{group.get('groupName', '')} - {brand.get('id', '')}"
                                    })
                                    seq += 1
    
    # If data is a dict with 'brands' key (from user's sample)
    if isinstance(data, dict) and 'brands' in data:
        for brand in data.get('brands', []):
            results.append({
                '序号': seq,
                '品牌brand': brand.get('name', ''),
                '系列类型Series type': f"Initial: {brand.get('initial', '')} - ID: {brand.get('id', '')}"
            })
            seq += 1
    
    return results


def export_to_csv(data: List[Dict], output_file: str = None):
    """Export to CSV file"""
    if not output_file:
        output_file = f"table_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    if not data:
        print("No data to export!")
        return None
    
    fieldnames = ['序号', '品牌brand', '系列类型Series type']
    
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='|')
        writer.writeheader()
        writer.writerows(data)
    
    print(f"[EXPORTED] {output_file}")
    return output_file


def export_to_txt(data: List[Dict], output_file: str = None):
    """Export to TXT file with table format"""
    if not output_file:
        output_file = f"table_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    if not data:
        print("No data to export!")
        return None
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("序号 | 品牌brand | 系列类型Series type\n")
        f.write("-" * 80 + "\n")
        
        # Data rows
        for row in data:
            f.write(f"{row['序号']} | {row['品牌brand']} | {row['系列类型Series type']}\n")
    
    print(f"[EXPORTED] {output_file}")
    return output_file


def print_table(data: List[Dict], limit: int = 20):
    """Print table to console"""
    print("\n" + "=" * 80)
    print("序号 | 品牌brand | 系列类型Series type")
    print("-" * 80)
    
    for i, row in enumerate(data):
        if i >= limit:
            print(f"... and {len(data) - limit} more rows")
            break
        print(f"{row['序号']} | {row['品牌brand']} | {row['系列类型Series type']}")
    
    print("=" * 80)
    print(f"Total: {len(data)} rows")


def main():
    # Default to newest JSON file if no argument provided
    if len(sys.argv) < 2:
        import glob
        json_files = glob.glob("*.json")
        if not json_files:
            print("Usage: python export_table.py input.json [output.csv]")
            print("No JSON files found in current directory!")
            return
        
        # Use the largest/newest file
        json_files.sort(key=lambda x: -len(open(x, 'rb').read()))
        input_file = json_files[0]
        print(f"Using: {input_file}")
    else:
        input_file = sys.argv[1]
    
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"\n[LOADING] {input_file}")
    data = load_json(input_file)
    
    print("[EXTRACTING] Brands and Series...")
    results = extract_brands_and_series(data)
    
    if results:
        # Print preview
        print_table(results)
        
        # Export to CSV
        csv_file = export_to_csv(results, output_file)
        
        # Export to TXT
        txt_file = output_file.replace('.csv', '.txt') if output_file else None
        export_to_txt(results, txt_file)
        
        print(f"\n[DONE] Exported {len(results)} rows")
    else:
        print("[WARNING] No data extracted! Check JSON structure.")


if __name__ == "__main__":
    main()
