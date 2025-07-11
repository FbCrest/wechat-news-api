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

# -- Bảng từ chuyên ngành --
GLOSSARY = {
    "沧澜": "Thương Lan",
    "潮光": "Triều Quang",
    "玄机": "Huyền Cơ",
    "龙吟": "Long Ngâm",
    "神相": "Thần Tương",
    "血河": "Huyết Hà",
    "碎梦": "Toái Mộng",
    "素问": "Tố Vấn",
    "九灵": "Cửu Linh",
    "铁衣": "Thiết Y"
}

# -- Làm sạch text dịch --
def cleanup_translation(text):
    text = re.sub(r"\*\*.*?\*\*", "", text)
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

# -- Thay thế tên riêng chuyên ngành còn sót --
def fix_terms(text):
    for zh, vi in GLOSSARY.items():
        text = text.replace(zh, vi)
    return text

# -- Hàm dịch nhiều tiêu đề cùng lúc --
def batch_translate_zh_to_vi(titles):
    numbered_list = "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles)])
    prompt = (
        "Bạn là chuyên gia dịch thuật tiếng Trung. "
        "Hãy dịch toàn bộ danh sách tiêu đề sau sang tiếng Việt tự nhiên, "
        "giữ đúng nghĩa trong bối cảnh là các thông báo và tin tức trong game di động Nghịch Thủy Hàn Mobile.\n\n"
        "Lưu ý:\n"
        "- Nếu tiêu đề chứa các từ sau thì bắt buộc dịch đúng theo bảng tra:\n"
        "- 沧澜 = Thương Lan\n"
        "- 潮光 = Triều Quang\n"
        "- 玄机 = Huyền Cơ\n"
        "- 龙吟 = Long Ngâm\n"
        "- 神相 = Thần Tương\n"
        "- 血河 = Huyết Hà\n"
        "- 碎梦 = Toái Mộng\n"
        "- 素问 = Tố Vấn\n"
        "- 九灵 = Cửu Linh\n"
        "- 铁衣 = Thiết Y\n\n"
        "Mỗi câu dịch trên một dòng, không thêm chú thích, không thêm số thứ tự:\n\n"
        + numbered_list
    )
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
        clean_text = cleanup_translation(raw_text)
        lines = [fix_terms(line.strip()) for line in clean_text.split("\n") if line.strip()]
        return lines
    else:
        print("❌ Lỗi dịch:", response.status_code, response.text)
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
            "title_zh": article["title"],
            "title_vi": vi_title,
            "url": article["url"],
            "cover_img": article["cover_img"],
            "date": article["date"]
        })

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! File news.json đã tạo.")
