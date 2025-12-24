# 🔍 Aihuishou Scraper

Scraper tool for aihuishou.com - Extract product data and export to Excel/CSV/JSON.

## 🚀 Quick Start

### Run Web UI
```bash
python app.py
# Open http://localhost:5000
```

### Run Command Line
```bash
# Scrape any URL
python url_scraper.py "https://m.aihuishou.com/n/#/category?frontCategoryId=6"

# Scrape with brand filter
python simple_scraper.py 6 苹果

# Product lookup
python aihuishou_scraper.py "https://m.aihuishou.com/n/#/inquiry?productId=43510" --xlsx
```

## 📁 Files

| File | Description |
|------|-------------|
| `app.py` | Web UI - paste URL → scrape → export |
| `url_scraper.py` | CLI - any URL → JSON output |
| `simple_scraper.py` | CLI - category/brand scraping |
| `aihuishou_scraper.py` | Product detail lookup with export |
| `full_scraper.py` | Scrape all categories |

## 🌐 Deploy

### Local (Windows)
```bash
python app.py
# Access: http://localhost:5000
# Network: http://192.168.1.49:5000
```

### Docker
```bash
docker build -t aihuishou-scraper .
docker run -d -p 5000:5000 aihuishou-scraper
```

### Google Cloud Run
```bash
# Install gcloud SDK first
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
deploy-gcp.bat
```

### GitHub Actions (Auto Deploy)
Add secrets to your repo:
- `GCP_PROJECT_ID` - Your GCP project ID
- `GCP_SA_KEY` - Service account JSON key

Push to `main` branch → auto deploy to Cloud Run.

## 📊 Export Formats

- **JSON** - Raw data with all fields
- **CSV** - UTF-8 with BOM (Excel compatible)
- **Excel** - .xlsx format

## 🔧 Requirements

```
flask
pandas
openpyxl
playwright
requests
```

Install:
```bash
pip install -r requirements.txt
playwright install chromium
```

## 📝 License

MIT
