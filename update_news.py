import requests
import json
import os
import time

# --- Cấu hình ---
ALBUM_URL = "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzU5NjU1NjY1Mw==&action=getalbum&album_id=3447004682407854082"
API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-1.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY}"

# --- Hàm dịch ---
def translate_zh_to_vi(text_zh):
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": f"Dịch sang tiếng Việt tự nhiên: {text_zh}"}]}
        ]
    }
    resp = requests.post(API_URL, headers=headers, json=payload)
    if resp.status_code == 200:
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        print("❌ Lỗi dịch:", resp.status_code, resp.text)
        return text_zh

# --- Lấy JSON từ WeChat ---
def fetch_album_data():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    resp = requests.get(ALBUM_URL, headers=headers)
    html = resp.text

    start = html.find("{\"getalbum_resp\"")
    end = html.find("}}") + 2
    json_text = html[start:end]

    data = json.loads(json_text)
    return data["getalbum_resp"]["article_list"]

# --- Chạy ---
if __name__ == "__main__":
    articles = fetch_album_data()
    print(f"✅ Lấy {len(articles)} bài viết.")

    news_list = []
    for idx, article in enumerate(articles, 1):
        title_zh = article["title"]
        url = article["url"]
        cover_img = article.get("cover_img_1_1")
        timestamp = int(article["create_time"])
        date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

        print(f"\n🌐 [{idx}] Dịch: {title_zh}")
        title_vi = translate_zh_to_vi(title_zh)
        print(f"➡️ {title_vi}")

        news_list.append({
            "date": date,
            "title": title_vi,
            "url": url,
            "cover_img": cover_img
        })

        time.sleep(1)

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! File news.json đã tạo.")
