import requests
import json
import time
import os

# --- Cấu hình ---
ALBUM_URL = "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzU5NjU1NjY1Mw==&action=getalbum&album_id=3447004682407854082"
API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-1.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY}"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
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

# --- Lấy dữ liệu JSON từ HTML ---
def fetch_album_data():
    print("🔍 Đang tải dữ liệu album...")
    resp = requests.get(ALBUM_URL, headers=HEADERS)
    html = resp.text

    start = html.find('{"getalbum_resp"')
    if start == -1:
        print("❌ Không tìm thấy JSON bắt đầu bằng 'getalbum_resp'")
        return []

    end = html.find('}}', start)
    if end == -1:
        print("❌ Không tìm thấy phần kết thúc JSON")
        return []

    json_text = html[start:end + 2]

    try:
        data = json.loads(json_text)
        articles = data["getalbum_resp"]["article_list"]
        print(f"✅ Tìm thấy {len(articles)} bài viết.")
        return articles
    except json.JSONDecodeError as e:
        print("❌ Lỗi JSON:", e)
        return []

# --- Chạy chính ---
if __name__ == "__main__":
    articles = fetch_album_data()
    if not articles:
        print("⚠️ Không có dữ liệu bài viết.")
        exit(0)

    news_list = []
    for idx, art in enumerate(articles, 1):
        title = art["title"]
        url = art["url"]
        cover_img = art["cover_img_1_1"]
        timestamp = int(art["create_time"])

        print(f"\n🌐 [{idx}] Dịch tiêu đề: {title}")
        translated = translate_zh_to_vi(title)
        print(f"➡️ {translated}")

        news_list.append({
            "title": translated,
            "url": url,
            "cover_img": cover_img,
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        })

        time.sleep(1)

    # --- Xuất file JSON ---
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! File news.json đã tạo.")
