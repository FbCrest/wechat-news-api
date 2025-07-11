import requests
import json
import time
import os
import re
from datetime import datetime

# -- Cấu hình --
WECHAT_JSON_URL = "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzU5NjU1NjY1Mw==&album_id=3447004682407854082&f=json"
API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-1.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY}"

# -- Hàm làm sạch text dịch --
def cleanup_translation(text):
    # Xóa phần giải thích hoặc markdown
    text = re.sub(r"\*\*.*?\*\*", "", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

# -- Hàm dịch --
def translate_zh_to_vi(text_zh):
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": f"Hãy dịch câu sau sang tiếng Việt tự nhiên, chỉ trả về đúng câu đã dịch, không thêm bất cứ chú thích nào: {text_zh}"}]}
        ]
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        print("❌ Lỗi dịch:", response.status_code, response.text)
        return text_zh

# -- Lấy dữ liệu từ JSON API của WeChat --
def fetch_articles(url):
    print("🔍 Đang lấy dữ liệu JSON từ WeChat...")
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    data = resp.json()

    articles_raw = data.get("getalbum_resp", {}).get("article_list", [])
    items = []
    for art in articles_raw:
        title = art["title"]
        url = art["url"]
        cover = art.get("cover_img_1_1") or art.get("cover") or ""
        timestamp = int(art.get("create_time", 0))
        date_str = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        items.append({
            "title": title,
            "url": url,
            "cover_img": cover,
            "date": date_str
        })

    print(f"✅ Đã lấy {len(items)} bài viết.")
    return items

# -- Chạy chính --
if __name__ == "__main__":
    articles = fetch_articles(WECHAT_JSON_URL)

    news_list = []
    for idx, article in enumerate(articles, 1):
        print(f"\n🌐 [{idx}] Dịch: {article['title']}")
        translated_raw = translate_zh_to_vi(article["title"])
        translated = cleanup_translation(translated_raw)
        # Kiểm tra còn ký tự tiếng Trung không
        if re.search(r'[\u4e00-\u9fff]', translated):
            print("⚠️ Cảnh báo: Dịch chưa hoàn chỉnh!")
        print(f"➡️ {translated}")
        news_list.append({
            "title_vi": translated,
            "url": article["url"],
            "cover_img": article["cover_img"],
            "date": article["date"]
        })
        time.sleep(1)  # tránh spam API

    # -- Ghi file --
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! File news.json đã tạo.")
