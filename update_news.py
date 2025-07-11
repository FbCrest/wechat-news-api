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

# -- Làm sạch text dịch --
def cleanup_translation(text):
    text = re.sub(r"\*\*.*?\*\*", "", text)
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

# -- Hàm dịch nhiều câu cùng lúc --
def batch_translate_zh_to_vi(titles):
    # Chuẩn bị prompt
    numbered_list = "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles)])
    prompt = (
        "Dịch toàn bộ danh sách sau sang tiếng Việt tự nhiên, "
        "mỗi câu dịch trên một dòng, không thêm bất kỳ chú thích nào:\n\n"
        + numbered_list
    )
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }
    # Gửi request
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
        # Làm sạch
        clean_text = cleanup_translation(raw_text)
        # Tách từng dòng
        lines = [l.strip("0123456789. \t") for l in clean_text.split("\n") if l.strip()]
        return lines
    else:
        print("❌ Lỗi dịch:", response.status_code, response.text)
        # Trả nguyên văn nếu lỗi
        return titles

# -- Lấy dữ liệu từ JSON API --
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

    zh_titles = [a["title"] for a in articles]
    print("\n🌐 Đang dịch tất cả tiêu đề...")
    vi_titles = batch_translate_zh_to_vi(zh_titles)

    news_list = []
    for i, article in enumerate(articles):
        vi_title = vi_titles[i] if i < len(vi_titles) else article["title"]
        if re.search(r'[\u4e00-\u9fff]', vi_title):
            print(f"⚠️ Bài {i+1}: Dịch chưa hoàn chỉnh!")
        print(f"➡️ {vi_title}")
        news_list.append({
            "title_vi": vi_title,
            "url": article["url"],
            "cover_img": article["cover_img"],
            "date": article["date"]
        })

    # Ghi file
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! File news.json đã tạo.")
