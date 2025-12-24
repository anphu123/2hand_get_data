# Configuration for Aihuishou Scraper

BASE_URL = "https://dubai.aihuishou.com/dubai-gateway"

# Default city IDs
CITIES = {
    "shanghai": 1,
    "beijing": 2,
    "guangzhou": 3,
    "shenzhen": 4,
}

DEFAULT_CITY_ID = 1  # Shanghai

# Request headers - cần giả lập browser thật
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://m.aihuishou.com",
    "Referer": "https://m.aihuishou.com/",
    "x-city-id": "1",
    "x-host-type": "2",
}

# Cookie template - URL encoded to avoid encoding errors
def get_cookies(city_id: int = 1, city_name: str = "上海市"):
    import json
    from urllib.parse import quote
    city_data = json.dumps({"id": city_id, "name": city_name}, ensure_ascii=False)
    return {
        "chosenCity": quote(city_data, safe=''),
    }

