import requests
import json
import time
import os
import re
from datetime import datetime

# -- Cấu hình --
API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-1.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY}"

ALBUMS = [
    # Album 1
    "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzU5NjU1NjY1Mw==&album_id=3447004682407854082&f=json",
    # Album 2
    "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzkyMjc1NzEzOA==&album_id=3646379824391471108&f=json",
    # Album 3
    "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzI1MDQ1MjUxNw==&album_id=3664489989179457545&f=json"
]

# -- Bảng từ chuyên ngành + dịch album --
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

# -- Thay thế tên riêng chuyên ngành --
def fix_terms(text):
    for zh, vi in GLOSSARY.items():
        text = text.replace(zh, vi)
    return text

# -- Dịch nhiều tiêu đề tiếng Trung sang tiếng Việt --
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

# -- Lấy bài viết từ 1 album --
def fetch_articles(url):
    print("🔍 Đang lấy dữ liệu từ album...")
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    data = resp.json()

    album_name_zh = data.get("getalbum_resp", {}).get("album_name", "Không rõ album")

    articles_raw = data.get("getalbum_resp", {}).get("article_list", [])
    items = []

    weekdays_vi = [
        "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm",
        "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"
    ]

    for art in articles_raw:
        title = art["title"]
        url = art["url"]
        cover = art.get("cover_img_1_1") or art.get("cover") or ""
        timestamp = int(art.get("create_time", 0))
        dt = datetime.utcfromtimestamp(timestamp)
        weekday = weekdays_vi[dt.weekday()]
        date_str = f"{dt.strftime('%H:%M')} - {weekday}, {dt.strftime('%d/%m')}"

        items.append({
            "title": title,
            "url": url,
            "cover_img": cover,
            "timestamp": timestamp,
            "date": date_str,
            "album": album_name_zh
        })

    print(f"✅ {len(items)} bài từ album: {album_name_zh}")
    return items

# -- Lấy 4 bài mới nhất từ mỗi album, gom lại & sắp xếp --
def fetch_all_albums(album_urls):
    all_articles = []
    for url in album_urls:
        articles = fetch_articles(url)
        top_4 = sorted(articles, key=lambda x: x["timestamp"], reverse=True)[:4]
        all_articles.extend(top_4)
    sorted_articles = sorted(all_articles, key=lambda x: x["timestamp"], reverse=True)
    return sorted_articles

# -- MAIN --
if __name__ == "__main__":
    articles = fetch_all_albums(ALBUMS)

    # Dịch tiêu đề bài viết
    zh_titles = [a["title"] for a in articles]
    print("\n🌐 Đang dịch tất cả tiêu đề...")
    vi_titles = batch_translate_zh_to_vi(zh_titles)

    # Dịch tên album
    zh_album_names = list(set([a["album"] for a in articles]))
    print("\n📚 Đang dịch tên các album...")
    vi_album_names = batch_translate_zh_to_vi(zh_album_names)
    album_dict = dict(zip(zh_album_names, vi_album_names))

    news_list = []
    for i, article in enumerate(articles):
        vi_title = vi_titles[i] if i < len(vi_titles) else article["title"]
        vi_album = album_dict.get(article["album"], article["album"])

        if re.search(r'[\u4e00-\u9fff]', vi_title):
            print(f"⚠️ Bài {i+1}: Dịch chưa hoàn chỉnh!")

        print(f"➡️ {vi_title}")
        news_list.append({
            "title_zh": article["title"],
            "title_vi": vi_title,
            "url": article["url"],
            "cover_img": article["cover_img"],
            "date": article["date"],
            "album": vi_album
        })

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! File news.json đã tạo.")
