import requests
from bs4 import BeautifulSoup
import json
import time
import os

# -- Cấu hình --
WECHAT_URL = "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzU5NjU1NjY1Mw==&action=getalbum&album_id=3447004682407854082"
API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-1.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY}"

# -- Hàm dịch --
def translate_zh_to_vi(text_zh):
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": f"Dịch sang tiếng Việt tự nhiên: {text_zh}"}]}
        ]
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        print("❌ Lỗi dịch:", response.status_code, response.text)
        return text_zh

# -- Lấy tiêu đề & link --
def fetch_titles_links(url):
    print("🔍 Đang lấy dữ liệu từ WeChat...")
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []

    for link in soup.find_all("a", class_="album__list-item"):
        title = link.get_text(strip=True)
        href = link["href"]
        if not href.startswith("http"):
            href = "https://mp.weixin.qq.com" + href
        items.append({"title": title, "url": href})

    print(f"✅ Đã lấy {len(items)} bài viết.")
    return items

# -- Chạy --
if __name__ == "__main__":
    articles = fetch_titles_links(WECHAT_URL)

    news_list = []
    for idx, article in enumerate(articles, 1):
        print(f"\n🌐 [{idx}] Dịch: {article['title']}")
        translated = translate_zh_to_vi(article["title"])
        print(f"➡️ {translated}")
        news_list.append({
            "title_zh": article["title"],
            "title_vi": translated,
            "url": article["url"]
        })
        time.sleep(1)

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! File news.json đã tạo.")
