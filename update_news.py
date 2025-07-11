import requests
from bs4 import BeautifulSoup
import json
import time
import os

# --- Cấu hình ---
ALBUM_URL = "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzU5NjU1NjY1Mw==&action=getalbum&album_id=3447004682407854082"
API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-1.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY}"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

# --- Hàm dịch tiếng Trung -> Việt ---
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

# --- Lấy danh sách bài viết ---
def fetch_articles():
    print("🔍 Đang tải dữ liệu album (HTML)...")
    resp = requests.get(ALBUM_URL, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    for idx, a in enumerate(soup.select("a.album__list-item"), 1):
        url = a["href"]
        if not url.startswith("http"):
            url = "https://mp.weixin.qq.com" + url
        title = a.get_text(strip=True)
        img_tag = a.find("img")
        cover_img = img_tag["data-src"] if img_tag and "data-src" in img_tag.attrs else ""
        date_tag = a.find("p", class_="album__item-publish")
        date_str = date_tag.get_text(strip=True) if date_tag else ""
        items.append({
            "title": title,
            "url": url,
            "cover_img": cover_img,
            "date": date_str
        })

    print(f"✅ Đã lấy {len(items)} bài viết.")
    return items

# --- Chạy chính ---
if __name__ == "__main__":
    articles = fetch_articles()
    if not articles:
        print("⚠️ Không có dữ liệu bài viết.")
        exit(0)

    news_list = []
    for idx, art in enumerate(articles, 1):
        print(f"\n🌐 [{idx}] Dịch tiêu đề: {art['title']}")
        translated = translate_zh_to_vi(art["title"])
        print(f"➡️ {translated}")
        news_list.append({
            "title": translated,
            "url": art["url"],
            "cover_img": art["cover_img"],
            "date": art["date"]
        })
        time.sleep(1)

    # --- Xuất file JSON ---
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! File news.json đã tạo.")
