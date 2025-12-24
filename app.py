"""
AIHUISHOU WEB SCRAPER
Simple UI - Just paste URL and get data
Export to JSON/CSV

Run: python app.py
Open: http://localhost:5000
"""

from flask import Flask, render_template_string, request, jsonify, Response, g
import asyncio
import sys
import io
import json
import csv
import time
import logging
from datetime import datetime
from functools import wraps

# Set UTF-8 encoding for Windows console (safe version)
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

# ============ LOGGING CONFIGURATION ============
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Create logger
logger = logging.getLogger('aihuishou')
logger.setLevel(logging.DEBUG)

# File handler - detailed logs
file_handler = logging.FileHandler(
    os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log"),
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
file_handler.setFormatter(file_formatter)

# Console handler - info only
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '\033[36m%(asctime)s\033[0m | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

app = Flask(__name__)


# ============ REQUEST LOGGING MIDDLEWARE ============
@app.before_request
def before_request():
    """Log incoming requests and start timer"""
    g.start_time = time.perf_counter()
    g.request_id = f"{datetime.now().strftime('%H%M%S')}-{id(request) % 10000:04d}"
    
    logger.info(f"[{g.request_id}] ▶ {request.method} {request.path}")
    
    if request.is_json and request.data:
        try:
            body = request.get_json()
            logger.debug(f"[{g.request_id}] Body: {json.dumps(body, ensure_ascii=False)[:200]}")
        except:
            pass


@app.after_request
def after_request(response):
    """Log response and timing"""
    elapsed = (time.perf_counter() - g.start_time) * 1000
    
    status_emoji = "✅" if response.status_code < 400 else "❌"
    logger.info(f"[{g.request_id}] {status_emoji} {response.status_code} | {elapsed:.0f}ms")
    
    # Log response size for API calls
    if request.path.startswith('/api/'):
        size = len(response.data) if response.data else 0
        logger.debug(f"[{g.request_id}] Response size: {size/1024:.1f}KB")
    
    return response


# ============ AUTO EXPORT FUNCTION ============
def auto_export(data, prefix="auto"):
    """Auto-save scraped data to files"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_dir = "exports"
    os.makedirs(export_dir, exist_ok=True)
    
    # Count items
    item_count = 0
    if isinstance(data, dict) and 'products' in data:
        item_count = len(data.get('products', []))
    elif isinstance(data, list):
        item_count = len(data)
    
    if item_count == 0:
        logger.warning("No data to auto-export")
        return None
    
    # Save JSON
    json_file = os.path.join(export_dir, f"{prefix}_{timestamp}.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"📁 Auto-exported: {json_file} ({item_count} items)")
    return json_file



HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aihuishou Scraper</title>
    <style>
        :root {
            --bg: #0a0a1a;
            --card: #12122a;
            --accent: #00d4ff;
            --accent2: #7c3aed;
            --text: #fff;
            --muted: #8892b0;
            --success: #10b981;
            --warning: #f59e0b;
            --border: rgba(255,255,255,0.08);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        
        header { text-align: center; margin-bottom: 40px; }
        h1 {
            font-size: 2.5rem;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .subtitle { color: var(--muted); font-size: 1.1rem; }
        
        .input-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
        }
        .input-group { display: flex; gap: 15px; flex-wrap: wrap; }
        input[type="text"] {
            flex: 1; min-width: 300px;
            padding: 16px 20px;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: rgba(255,255,255,0.03);
            color: var(--text);
            font-size: 16px;
            outline: none;
            transition: all 0.3s;
        }
        input:focus { border-color: var(--accent); box-shadow: 0 0 20px rgba(0,212,255,0.15); }
        
        .btn {
            padding: 16px 40px; border: none; border-radius: 12px;
            font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s;
        }
        .btn-primary { background: linear-gradient(135deg, var(--accent), var(--accent2)); color: #fff; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(0,212,255,0.3); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        
        .results-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 30px;
            display: none;
        }
        .results-card.show { display: block; }
        
        .results-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 20px; padding-bottom: 15px;
            border-bottom: 1px solid var(--border);
            flex-wrap: wrap; gap: 10px;
        }
        .count-badge { background: var(--success); padding: 6px 16px; border-radius: 20px; font-size: 14px; font-weight: 600; }
        
        .export-btns { display: flex; gap: 10px; flex-wrap: wrap; }
        .btn-export {
            padding: 10px 20px; border: 1px solid var(--accent); border-radius: 8px;
            background: transparent; color: var(--accent); font-size: 14px;
            cursor: pointer; transition: all 0.2s;
        }
        .btn-export:hover { background: var(--accent); color: var(--bg); }
        
        /* Column Customization Panel */
        .custom-panel {
            background: rgba(0,0,0,0.3);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .panel-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 15px; cursor: pointer;
        }
        .panel-header h4 { color: var(--accent); }
        .panel-toggle { color: var(--muted); font-size: 20px; }
        .panel-content { display: none; }
        .panel-content.show { display: block; }
        
        .column-list {
            display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 15px;
        }
        .column-item {
            display: flex; align-items: center; gap: 8px;
            padding: 8px 12px;
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            border-radius: 8px;
            cursor: grab;
            transition: all 0.2s;
        }
        .column-item:hover { border-color: var(--accent); }
        .column-item.dragging { opacity: 0.5; border-color: var(--accent2); }
        .column-item input[type="checkbox"] { accent-color: var(--accent); }
        .column-item input[type="text"] {
            width: 120px; padding: 4px 8px; font-size: 12px;
            background: rgba(0,0,0,0.3); border: 1px solid var(--border);
            border-radius: 4px; color: var(--text);
        }
        .column-item .field-name { color: var(--muted); font-size: 11px; }
        
        .custom-actions { display: flex; gap: 10px; margin-top: 15px; }
        .btn-small {
            padding: 8px 16px; border: 1px solid var(--border); border-radius: 6px;
            background: transparent; color: var(--muted); font-size: 12px;
            cursor: pointer; transition: all 0.2s;
        }
        .btn-small:hover { border-color: var(--accent); color: var(--accent); }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border); }
        th { color: var(--accent); font-weight: 600; background: rgba(0,212,255,0.05); }
        tr:hover { background: rgba(0,212,255,0.03); }
        td { font-size: 14px; }
        
        .loading { display: none; text-align: center; padding: 40px; }
        .loading.show { display: block; }
        .spinner {
            width: 40px; height: 40px;
            border: 3px solid var(--border); border-top-color: var(--accent);
            border-radius: 50%; animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        @keyframes spin { to { transform: rotate(360deg); }}
        
        .status {
            position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
            padding: 12px 25px; background: var(--card);
            border: 1px solid var(--accent); border-radius: 10px;
            display: none; z-index: 100;
        }
        .status.show { display: block; }
        
        .raw-json {
            background: rgba(0,0,0,0.3); border-radius: 8px; padding: 15px;
            margin-top: 20px; max-height: 300px; overflow: auto;
            font-family: monospace; font-size: 12px; white-space: pre-wrap;
            display: none;
        }
        .raw-json.show { display: block; }
        
        .toggle-btns { display: flex; gap: 10px; margin-bottom: 15px; }
        .toggle-btn {
            padding: 8px 16px; border: 1px solid var(--border); border-radius: 8px;
            background: transparent; color: var(--muted); cursor: pointer; transition: all 0.2s;
        }
        .toggle-btn.active { border-color: var(--accent); color: var(--accent); background: rgba(0,212,255,0.1); }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Aihuishou Scraper</h1>
            <p class="subtitle">Paste URL → Get Data → Customize Columns → Export</p>
        </header>
        
        <div class="input-card">
            <div class="input-group">
                <input type="text" id="urlInput" placeholder="Paste aihuishou.com URL here...">
                <button class="btn btn-primary" id="scrapeBtn" onclick="scrape()">Scrape</button>
                <button class="btn btn-primary" id="deepScrapeBtn" onclick="deepScrape()" style="background: linear-gradient(135deg, #f59e0b, #ef4444);">🔥 Deep Scrape</button>
            </div>
            <p style="color: var(--muted); font-size: 12px; margin-top: 10px;">
                <b>Scrape</b>: Single page | <b>Deep Scrape</b>: Category → Brands → Series → Products (3 levels)
            </p>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p id="loadingText">Scraping data... This may take 15-30 seconds</p>
        </div>
        
        <div class="results-card" id="results">
            <div class="results-header">
                <h3>📦 Results</h3>
                <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                    <span class="count-badge" id="count">0 items</span>
                    <div class="export-btns">
                        <button class="btn-export" onclick="exportData('custom')">📋 Export Custom</button>
                        <button class="btn-export" onclick="exportData('json')">📄 JSON</button>
                    </div>
                </div>
            </div>
            
            <!-- Column Customization Panel -->
            <div class="custom-panel">
                <div class="panel-header" onclick="togglePanel()">
                    <h4>⚙️ Customize Columns (Click to expand)</h4>
                    <span class="panel-toggle" id="panelToggle">▼</span>
                </div>
                <div class="panel-content" id="panelContent">
                    <p style="color: var(--muted); margin-bottom: 10px; font-size: 13px;">
                        ✓ Check/uncheck to show/hide columns | ✏️ Edit header names | 🔄 Drag to reorder
                    </p>
                    <div class="column-list" id="columnList"></div>
                    <div class="custom-actions">
                        <button class="btn-small" onclick="selectAllColumns()">Select All</button>
                        <button class="btn-small" onclick="deselectAllColumns()">Deselect All</button>
                        <button class="btn-small" onclick="resetColumns()">Reset Default</button>
                        <button class="btn-small" onclick="applyColumns()" style="border-color: var(--success); color: var(--success);">✓ Apply Changes</button>
                    </div>
                </div>
            </div>
            
            <div class="toggle-btns">
                <button class="toggle-btn active" onclick="switchView('table')">📋 Table View</button>
                <button class="toggle-btn" onclick="switchView('raw')">📄 Raw JSON</button>
            </div>
            
            <div id="tableView" style="overflow-x: auto;">
                <table>
                    <thead id="tableHead"><tr></tr></thead>
                    <tbody id="tableBody"></tbody>
                </table>
            </div>
            <div class="raw-json" id="rawJson"></div>
        </div>
    </div>
    
    <div class="status" id="status"></div>
    
    <script>
        let currentData = [];
        let allFields = [];  // All available fields from data
        let selectedColumns = [];  // User selected columns with custom headers
        let draggedItem = null;
        
        // Default column config - works for both normal scrape and deep scrape
        // Other fields available in custom panel (⚙️ Customize Columns)
        const defaultColumns = [
            { field: '序号', header: '序号', enabled: true, isIndex: true },
            { field: 'brand', header: '品牌brand', enabled: true },
            { field: 'series', header: '系列Series', enabled: true },
            { field: 'productName', header: '产品ProductName', enabled: true },
            { field: 'name', header: 'Name', enabled: false },
            { field: 'title', header: 'Title', enabled: false }
        ];
        
        async function scrape() {
            const url = document.getElementById('urlInput').value.trim();
            if (!url) { showStatus('Please enter a URL'); return; }
            
            document.getElementById('scrapeBtn').disabled = true;
            document.getElementById('loading').classList.add('show');
            document.getElementById('results').classList.remove('show');
            
            try {
                const res = await fetch('/api/scrape', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url})
                });
                const data = await res.json();
                
                if (data.error) {
                    showStatus('Error: ' + data.error);
                } else {
                    displayResults(data);
                }
            } catch (e) {
                showStatus('Error: ' + e.message);
            }
            
            document.getElementById('scrapeBtn').disabled = false;
            document.getElementById('loading').classList.remove('show');
        }
        
        // Deep Scrape: Category → Brands → Series → Products
        async function deepScrape() {
            const url = document.getElementById('urlInput').value.trim();
            if (!url) { showStatus('Please enter a category URL'); return; }
            
            document.getElementById('scrapeBtn').disabled = true;
            document.getElementById('deepScrapeBtn').disabled = true;
            document.getElementById('loadingText').textContent = 'Deep scraping... This may take 2-5 minutes (Category → Brands → Series → Products)';
            document.getElementById('loading').classList.add('show');
            document.getElementById('results').classList.remove('show');
            
            try {
                const res = await fetch('/api/deep-scrape', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url})
                });
                const data = await res.json();
                
                if (data.error) {
                    showStatus('Error: ' + data.error);
                } else {
                    displayResults(data);
                }
            } catch (e) {
                showStatus('Error: ' + e.message);
            }
            
            document.getElementById('scrapeBtn').disabled = false;
            document.getElementById('deepScrapeBtn').disabled = false;
            document.getElementById('loadingText').textContent = 'Scraping data... This may take 15-30 seconds';
            document.getElementById('loading').classList.remove('show');
        }
        
        function displayResults(data) {
            // ONLY use products - cleaner default view
            let items = [];
            
            // Priority: products from SPU list
            if (data.products?.length) {
                items = data.products;
            }
            
            // Remove duplicates
            const seen = new Set();
            items = items.filter(item => {
                if (item.id && seen.has(item.id)) return false;
                if (item.id) seen.add(item.id);
                return true;
            });
            
            currentData = items;
            
            // Extract all unique fields from data
            allFields = ['序号'];  // Always include index
            items.forEach(item => {
                Object.keys(item).forEach(key => {
                    if (!allFields.includes(key)) allFields.push(key);
                });
            });
            
            // Initialize columns with defaults + detected fields
            initializeColumns();
            
            document.getElementById('count').textContent = items.length + ' products';
            document.getElementById('rawJson').textContent = JSON.stringify(data, null, 2);
            document.getElementById('results').classList.add('show');
            
            buildColumnList();
            renderTable();
            showStatus('Found ' + items.length + ' products');
        }
        
        function initializeColumns() {
            selectedColumns = [...defaultColumns];
            
            // Add other detected fields as disabled by default
            allFields.forEach(field => {
                if (field !== '序号' && !selectedColumns.find(c => c.field === field)) {
                    selectedColumns.push({
                        field: field,
                        header: field,
                        enabled: false,
                        isIndex: false
                    });
                }
            });
        }
        
        function buildColumnList() {
            const container = document.getElementById('columnList');
            container.innerHTML = selectedColumns.map((col, idx) => `
                <div class="column-item" draggable="true" data-index="${idx}"
                     ondragstart="dragStart(event)" ondragover="dragOver(event)" 
                     ondrop="drop(event)" ondragend="dragEnd(event)">
                    <input type="checkbox" ${col.enabled ? 'checked' : ''} 
                           onchange="toggleColumn(${idx}, this.checked)">
                    <div>
                        <input type="text" value="${col.header}" 
                               onchange="updateHeader(${idx}, this.value)"
                               placeholder="Header name">
                        <div class="field-name">Field: ${col.field}</div>
                    </div>
                </div>
            `).join('');
        }
        
        function toggleColumn(idx, enabled) {
            selectedColumns[idx].enabled = enabled;
        }
        
        function updateHeader(idx, newHeader) {
            selectedColumns[idx].header = newHeader;
        }
        
        function selectAllColumns() {
            selectedColumns.forEach(c => c.enabled = true);
            buildColumnList();
        }
        
        function deselectAllColumns() {
            selectedColumns.forEach(c => c.enabled = false);
            buildColumnList();
        }
        
        function resetColumns() {
            initializeColumns();
            buildColumnList();
            renderTable();
            showStatus('Columns reset to default');
        }
        
        function applyColumns() {
            renderTable();
            showStatus('Table updated!');
        }
        
        function renderTable() {
            const enabledCols = selectedColumns.filter(c => c.enabled);
            
            // Build header
            document.getElementById('tableHead').innerHTML = `
                <tr>${enabledCols.map(c => `<th>${c.header}</th>`).join('')}</tr>
            `;
            
            // Build body
            document.getElementById('tableBody').innerHTML = currentData.slice(0, 200).map((item, idx) => `
                <tr>${enabledCols.map(c => {
                    let value = c.isIndex ? (idx + 1) : (item[c.field] ?? '-');
                    if (typeof value === 'object') value = JSON.stringify(value);
                    return `<td>${value}</td>`;
                }).join('')}</tr>
            `).join('');
        }
        
        // Drag and drop for reordering
        function dragStart(e) {
            draggedItem = e.target.closest('.column-item');
            draggedItem.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        }
        
        function dragOver(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
        }
        
        function drop(e) {
            e.preventDefault();
            const target = e.target.closest('.column-item');
            if (!target || target === draggedItem) return;
            
            const fromIdx = parseInt(draggedItem.dataset.index);
            const toIdx = parseInt(target.dataset.index);
            
            // Reorder array
            const [moved] = selectedColumns.splice(fromIdx, 1);
            selectedColumns.splice(toIdx, 0, moved);
            
            buildColumnList();
        }
        
        function dragEnd(e) {
            if (draggedItem) draggedItem.classList.remove('dragging');
            draggedItem = null;
        }
        
        function togglePanel() {
            const content = document.getElementById('panelContent');
            const toggle = document.getElementById('panelToggle');
            content.classList.toggle('show');
            toggle.textContent = content.classList.contains('show') ? '▲' : '▼';
        }
        
        function switchView(view) {
            const btns = document.querySelectorAll('.toggle-btn');
            btns.forEach(b => b.classList.remove('active'));
            
            if (view === 'table') {
                document.getElementById('tableView').style.display = 'block';
                document.getElementById('rawJson').classList.remove('show');
                btns[0].classList.add('active');
            } else {
                document.getElementById('tableView').style.display = 'none';
                document.getElementById('rawJson').classList.add('show');
                btns[1].classList.add('active');
            }
        }
        
        function exportData(format) {
            if (!currentData.length) { showStatus('No data to export'); return; }
            
            let content, filename, type;
            const timestamp = new Date().toISOString().slice(0,19).replace(/[:-]/g,'');
            
            if (format === 'json') {
                content = JSON.stringify(currentData, null, 2);
                filename = `aihuishou_${timestamp}.json`;
                type = 'application/json';
            } else {
                // Export with custom columns - CSV format
                const enabledCols = selectedColumns.filter(c => c.enabled);
                const sep = ',';
                const nl = String.fromCharCode(10);
                const bom = String.fromCharCode(0xFEFF);
                
                const headers = enabledCols.map(c => c.header).join(sep);
                const rows = currentData.map((item, idx) => 
                    enabledCols.map(c => {
                        let val = c.isIndex ? (idx + 1) : (item[c.field] || '');
                        if (typeof val === 'object') val = JSON.stringify(val);
                        return String(val).replace(/,/g, ';');
                    }).join(sep)
                );
                
                content = bom + headers + nl + rows.join(nl);
                filename = `aihuishou_${timestamp}.csv`;
                type = 'text/csv;charset=utf-8';
            }
            
            const blob = new Blob([content], {type});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            a.click();
            showStatus('Downloaded ' + filename);
        }
        
        function showStatus(msg) {
            const el = document.getElementById('status');
            el.textContent = msg;
            el.classList.add('show');
            setTimeout(() => el.classList.remove('show'), 3000);
        }
        
        document.getElementById('urlInput').addEventListener('keypress', e => {
            if (e.key === 'Enter') scrape();
        });
    </script>
</body>
</html>
"""

# ============ SCRAPER ============
async def scrape_url(url: str):
    from playwright.async_api import async_playwright
    
    captured = {"products": [], "brands": [], "raw": []}
    
    async def handle_response(response):
        if "aihuishou.com" not in response.url:
            return
        try:
            data = await response.json()
            if data.get("code") != 0:
                return
            resp_data = data.get("data")
            
            if resp_data:
                captured["raw"].append(resp_data)
            
            if isinstance(resp_data, list) and len(resp_data) > 0:
                first = resp_data[0]
                
                # SPU Product list (productId, productName, serials) - from spu-list page
                if "productId" in first and "productName" in first:
                    for item in resp_data:
                        product = {
                            "id": item.get("productId"),
                            "name": item.get("productName") or item.get("title"),
                            "title": item.get("title"),
                            "subTitle": item.get("subTitle"),
                            "imageUrl": item.get("imageUrl"),
                            "bizType": item.get("bizType"),
                            "categoryId": item.get("categoryId"),
                            "ppvList": ", ".join(item.get("ppvList", [])) if item.get("ppvList") else "",
                        }
                        # Extract series info
                        serials = item.get("serials")
                        if serials:
                            product["seriesCode"] = serials.get("code")
                            product["seriesName"] = serials.get("name")
                            product["seriesImage"] = serials.get("imageUrl")
                        captured["products"].append(product)
                
                # Price-based products (maxPrice)
                elif "maxPrice" in first:
                    captured["products"].extend(resp_data)
                
                # Brand list (iconUrl + name, no maxPrice)
                elif "iconUrl" in first and "name" in first and "maxPrice" not in first:
                    captured["brands"].extend(resp_data)
        except:
            pass
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
            viewport={"width": 375, "height": 812}
        )
        await context.add_cookies([{
            "name": "chosenCity",
            "value": "%7B%22id%22%3A1%2C%22name%22%3A%22%E4%B8%8A%E6%B5%B7%E5%B8%82%22%7D",
            "domain": "m.aihuishou.com",
            "path": "/"
        }])
        
        page = await context.new_page()
        page.on("response", lambda r: asyncio.create_task(handle_response(r)))
        
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(6)
        
        for _ in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.5)
        
        await browser.close()
    
    return captured


# ============ ROUTES ============
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    data = request.get_json()
    url = data.get('url', '')
    
    if not url:
        logger.warning("Scrape request with no URL")
        return jsonify({"error": "URL required"})
    
    logger.info(f"🔍 Starting scrape: {url[:60]}...")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(scrape_url(url))
    loop.close()
    
    # Auto-export
    product_count = len(result.get('products', []))
    if product_count > 0:
        auto_export(result, "scrape")
        logger.info(f"✅ Scrape complete: {product_count} products")
    
    return jsonify(result)


@app.route('/api/deep-scrape', methods=['POST'])
def api_deep_scrape():
    """Deep scrape: Category → Brands → Series → Products"""
    data = request.get_json()
    url = data.get('url', '')
    
    if not url:
        logger.warning("Deep scrape request with no URL")
        return jsonify({"error": "URL required"})
    
    logger.info(f"🔥 Starting DEEP scrape: {url[:60]}...")
    start_time = time.perf_counter()
    
    try:
        from deep_scraper import DeepScraper
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        scraper = DeepScraper()
        products = loop.run_until_complete(scraper.scrape_all(url, headless=True))
        loop.close()
        
        elapsed = time.perf_counter() - start_time
        result = {"products": products}
        
        # Auto-export
        if len(products) > 0:
            auto_export(result, "deep_scrape")
            logger.info(f"✅ Deep scrape complete: {len(products)} products in {elapsed:.1f}s")
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Deep scrape error: {str(e)}")
        return jsonify({"error": str(e)})


@app.route('/api/logs', methods=['GET'])
def api_logs():
    """Get recent logs"""
    try:
        log_file = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-100:]  # Last 100 lines
            return jsonify({"logs": lines})
    except Exception as e:
        return jsonify({"error": str(e)})
    return jsonify({"logs": []})


@app.route('/api/status', methods=['GET'])
def api_status():
    """Server status endpoint"""
    return jsonify({
        "status": "running",
        "time": datetime.now().isoformat(),
        "hostname": "192.168.1.11",
        "port": 5000
    })


if __name__ == '__main__':
    # Startup banner
    print()
    print("╔" + "═" * 48 + "╗")
    print("║" + "  AIHUISHOU SCRAPER SERVER".center(48) + "║")
    print("╠" + "═" * 48 + "╣")
    print("║" + f"  🌐 Local:   http://localhost:5000".ljust(48) + "║")
    print("║" + f"  🌐 Network: http://192.168.1.11:5000".ljust(48) + "║")
    print("║" + f"  📁 Logs:    {LOG_DIR}/".ljust(48) + "║")
    print("║" + f"  📦 Exports: exports/".ljust(48) + "║")
    print("╚" + "═" * 48 + "╝")
    print()
    
    logger.info("🚀 Server starting...")
    app.run(debug=True, host='0.0.0.0', port=5000)

