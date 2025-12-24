"""
Aihuishou Scraper Web UI
Simple Flask web interface for the scraper
"""

from flask import Flask, render_template, request, jsonify
import asyncio
import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper_browser import get_product_data

app = Flask(__name__)

# HTML template embedded
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aihuishou Scraper</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #fff;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        
        header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        h1 {
            font-size: 2.5rem;
            background: linear-gradient(90deg, #00d2ff, #3a7bd5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #8892b0;
            font-size: 1.1rem;
        }
        
        .search-box {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .input-group {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        input[type="text"] {
            flex: 1;
            min-width: 300px;
            padding: 15px 20px;
            border: none;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            font-size: 1rem;
            outline: none;
            transition: all 0.3s ease;
        }
        
        input[type="text"]:focus {
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 0 20px rgba(0, 210, 255, 0.3);
        }
        
        input[type="text"]::placeholder {
            color: #8892b0;
        }
        
        button {
            padding: 15px 40px;
            border: none;
            border-radius: 12px;
            background: linear-gradient(90deg, #00d2ff, #3a7bd5);
            color: #fff;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 210, 255, 0.4);
        }
        
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        
        .loading.active {
            display: block;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(255, 255, 255, 0.1);
            border-top-color: #00d2ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .result {
            display: none;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .result.active {
            display: block;
        }
        
        .product-header {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .product-icon {
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, #00d2ff, #3a7bd5);
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }
        
        .product-info h2 {
            font-size: 1.5rem;
            margin-bottom: 5px;
        }
        
        .product-info .price {
            color: #00d2ff;
            font-size: 1.2rem;
            font-weight: 600;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .info-card {
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 12px;
        }
        
        .info-card label {
            color: #8892b0;
            font-size: 0.85rem;
            display: block;
            margin-bottom: 5px;
        }
        
        .info-card span {
            font-size: 1.1rem;
            font-weight: 500;
        }
        
        .questions {
            margin-top: 25px;
        }
        
        .questions h3 {
            margin-bottom: 15px;
            color: #00d2ff;
        }
        
        .question-item {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 10px;
        }
        
        .question-item h4 {
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .question-item h4 .badge {
            background: #e74c3c;
            padding: 2px 8px;
            border-radius: 5px;
            font-size: 0.75rem;
            font-weight: normal;
        }
        
        .options {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .option-tag {
            background: rgba(0, 210, 255, 0.1);
            color: #00d2ff;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
        }
        
        .json-output {
            margin-top: 25px;
        }
        
        .json-output h3 {
            margin-bottom: 15px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .json-output pre {
            background: rgba(0, 0, 0, 0.3);
            padding: 20px;
            border-radius: 12px;
            overflow-x: auto;
            font-size: 0.85rem;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .error {
            background: rgba(231, 76, 60, 0.2);
            border: 1px solid #e74c3c;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }
        
        .error-icon {
            font-size: 3rem;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Aihuishou Scraper</h1>
            <p class="subtitle">Nhập link sản phẩm từ m.aihuishou.com để tra cứu thông tin</p>
        </header>
        
        <div class="search-box">
            <form id="searchForm">
                <div class="input-group">
                    <input type="text" id="urlInput" 
                           placeholder="https://m.aihuishou.com/n/#/inquiry?productId=43510" 
                           required>
                    <button type="submit" id="searchBtn">Tra cứu</button>
                </div>
            </form>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Đang lấy dữ liệu... Vui lòng chờ</p>
        </div>
        
        <div class="result" id="result"></div>
    </div>
    
    <script>
        const form = document.getElementById('searchForm');
        const urlInput = document.getElementById('urlInput');
        const searchBtn = document.getElementById('searchBtn');
        const loading = document.getElementById('loading');
        const result = document.getElementById('result');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const url = urlInput.value.trim();
            if (!url) return;
            
            // Show loading
            loading.classList.add('active');
            result.classList.remove('active');
            searchBtn.disabled = true;
            
            try {
                const response = await fetch('/api/scrape', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url})
                });
                
                const data = await response.json();
                displayResult(data);
            } catch (error) {
                result.innerHTML = `
                    <div class="error">
                        <div class="error-icon">❌</div>
                        <h3>Lỗi kết nối</h3>
                        <p>${error.message}</p>
                    </div>
                `;
                result.classList.add('active');
            } finally {
                loading.classList.remove('active');
                searchBtn.disabled = false;
            }
        });
        
        function displayResult(data) {
            if (data.error) {
                result.innerHTML = `
                    <div class="error">
                        <div class="error-icon">❌</div>
                        <h3>Lỗi</h3>
                        <p>${data.error}</p>
                    </div>
                `;
            } else {
                let questionsHtml = '';
                if (data.questions && data.questions.length > 0) {
                    questionsHtml = `
                        <div class="questions">
                            <h3>📝 Câu hỏi định giá (${data.questions.length} mục)</h3>
                            ${data.questions.map(q => `
                                <div class="question-item">
                                    <h4>
                                        ${q.name}
                                        ${q.isNoAdditional ? `<span class="badge">${q.noAdditionalTips || 'Không thu mua'}</span>` : ''}
                                    </h4>
                                    ${q.description ? `<p style="color: #8892b0; margin-bottom: 10px; font-size: 0.9rem;">${q.description}</p>` : ''}
                                    <div class="options">
                                        ${q.options.slice(0, 5).map(opt => `
                                            <span class="option-tag">${opt.name}</span>
                                        `).join('')}
                                        ${q.options.length > 5 ? `<span class="option-tag">+${q.options.length - 5} more</span>` : ''}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
                
                result.innerHTML = `
                    <div class="product-header">
                        <div class="product-icon">📱</div>
                        <div class="product-info">
                            <h2>${data.name || 'N/A'}</h2>
                            <div class="price">💰 Coupon: ${data.couponPrice || 0} CNY</div>
                        </div>
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-card">
                            <label>Product ID</label>
                            <span>${data.id || 'N/A'}</span>
                        </div>
                        <div class="info-card">
                            <label>Template Type</label>
                            <span>${data.templateType || 'N/A'}</span>
                        </div>
                    </div>
                    
                    ${questionsHtml}
                    
                    <div class="json-output">
                        <h3 onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">
                            📄 JSON Output (click to toggle)
                        </h3>
                        <pre style="display: none;">${JSON.stringify(data, null, 2)}</pre>
                    </div>
                `;
            }
            result.classList.add('active');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/api/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    url = data.get('url', '')
    
    if not url:
        return jsonify({"error": "URL is required"})
    
    # Run async function
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_product_data(url))
        loop.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    print("=" * 50)
    print("  AIHUISHOU SCRAPER WEB UI")
    print("  Open browser: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
