import requests
import json
import os
import re
import time
from datetime import datetime

# -- Cấu hình --
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")  # Đặt biến môi trường này bằng account_id của bạn
CLOUDFLARE_TRANSLATE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/m2m100-1.2b"

ALBUMS = [
    "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzU5NjU1NjY1Mw==&album_id=3447004682407854082&f=json",
    "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzkyMjc1NzEzOA==&album_id=3646379824391471108&f=json",
    "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzI1MDQ1MjUxNw==&album_id=3664489989179457545&f=json"
]

# -- Bảng từ chuyên ngành --
GLOSSARY = {
    "流": "lối chơi",
    "木桩": "cọc gỗ",
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

def cleanup_translation(text):
    text = re.sub(r"\*\*.*?\*\*", "", text)
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

def fix_terms(text):
    for zh, vi in GLOSSARY.items():
        text = text.replace(zh, vi)
    return text

def batch_translate_zh_to_vi(titles, retries=3, delay=10):
    """
    Dịch danh sách tiêu đề tiếng Trung sang tiếng Việt bằng Cloudflare AI Translate.
    """
    if not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_ACCOUNT_ID:
        print("❌ Thiếu CLOUDFLARE_API_TOKEN hoặc CLOUDFLARE_ACCOUNT_ID.")
        return titles
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    results = []
    for idx, text in enumerate(titles):
        payload = {
            "text": text,
            "source_lang": "zh",
            "target_lang": "vi"
        }
        for attempt in range(retries):
            try:
                resp = requests.post(CLOUDFLARE_TRANSLATE_URL, headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    vi_text = resp.json().get("result", "")
                    if isinstance(vi_text, dict):
                        vi_text = vi_text.get("text", "")
                    elif isinstance(vi_text, list):
                        if vi_text and isinstance(vi_text[0], str):
                            vi_text = vi_text[0]
                        else:
                            vi_text = ""
                    if not isinstance(vi_text, str) or not vi_text:
                        vi_text = text
                    vi_text = fix_terms(cleanup_translation(vi_text))
                    results.append(vi_text)
                    break
                else:
                    print(f"❌ Lỗi dịch dòng {idx+1}: {resp.status_code}: {resp.text}")
                    if attempt < retries - 1:
                        time.sleep(delay)
                    else:
                        results.append(text)
            except Exception as e:
                print(f"❌ Exception khi dịch dòng {idx+1}: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    results.append(text)
    return results

def fetch_articles(url):
    print("🔍 Đang lấy dữ liệu từ album...")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://mp.weixin.qq.com/",
        "X-Requested-With": "XMLHttpRequest"
    }
    resp = requests.get(url, headers=headers)
    data = resp.json()

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
            "date": date_str
        })

    print(f"✅ {len(items)} bài viết")
    return items

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

    print("\n🎉 Hoàn tất! Đã tạo file news.json.")
