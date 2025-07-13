import requests
import json
import os
import re
import time
from datetime import datetime

# -- Cấu hình --
API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-1.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY}"

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
    print(f"   - Gửi {len(titles)} tiêu đề đến API dịch...")
    joined_titles = "\n".join(titles)
    prompt = (
        "Bạn là một chuyên gia dịch thuật tiếng Trung - Việt, có hiểu biết sâu sắc về game mobile Trung Quốc, đặc biệt là 'Nghịch Thủy Hàn Mobile'.\n"
        "Hãy dịch tất cả các tiêu đề sau sang **tiếng Việt tự nhiên, súc tích, đúng văn phong giới game thủ Việt**, mang màu sắc hấp dẫn, ưu tiên giữ nguyên các thuật ngữ kỹ thuật, tên vật phẩm, và cấu trúc tiêu đề gốc.\n\n"
        "⚠️ Quy tắc dịch:\n"
        "- Giữ nguyên các cụm số (như 10W, 288).\n"
        "- Giữ nguyên tên kỹ năng, vũ khí, tính năng trong dấu [] hoặc 【】.\n"
        "- Ưu tiên từ ngữ phổ biến trong cộng đồng game như: 'build', 'phối đồ', 'đập đồ', 'lộ trình', 'trang bị xịn', 'ngoại hình đỉnh', 'top server'...\n"
        "- Các từ cố định phải dịch đúng theo bảng sau:\n"
        "- 流 = lối chơi\n"
        "- 木桩 = cọc gỗ\n"
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
        "🚫 Không được thêm bất kỳ ghi chú, số thứ tự, hoặc phần mở đầu. Chỉ dịch từng dòng, giữ nguyên thứ tự gốc.\n\n"
        + joined_titles
    )

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    for attempt in range(retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            response.raise_for_status()  # Sẽ báo lỗi cho các mã 4xx hoặc 5xx

            result = response.json()
            if "candidates" not in result or not result["candidates"]:
                print(f"   - ❌ Lỗi: Phản hồi API không hợp lệ ở lần thử {attempt + 1}. Thiếu 'candidates'.")
                continue # Thử lại

            raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
            clean_text = cleanup_translation(raw_text)
            lines = [fix_terms(line.strip()) for line in clean_text.split("\n") if line.strip()]
            print(f"   - ✅ Dịch thành công {len(lines)}/{len(titles)} tiêu đề.")
            return lines

        except requests.exceptions.RequestException as e:
            print(f"   - ❌ Lỗi kết nối mạng (lần {attempt + 1}/{retries}): {e}")
        except Exception as e:
            print(f"   - ❌ Lỗi không xác định (lần {attempt + 1}/{retries}): {e}")
        
        if attempt < retries - 1:
            print(f"   - ⚠️ Thử lại sau {delay} giây...")
            time.sleep(delay)

    print("   - ❌ Thử lại nhiều lần nhưng vẫn lỗi. Bỏ qua dịch.")
    return titles

def fetch_articles(url):
    print(f"   - 🚚 Đang lấy dữ liệu từ album: {url[:70]}...")
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

    print(f"      -> Tìm thấy {len(items)} bài viết.")
    return items

def fetch_all_albums(album_urls):
    print("\n---\n📰 Bắt đầu quá trình lấy tin tức từ các album...")
    all_articles = []
    for url in album_urls:
        articles = fetch_articles(url)
        top_4 = sorted(articles, key=lambda x: x["timestamp"], reverse=True)[:4]
        all_articles.extend(top_4)
    sorted_articles = sorted(all_articles, key=lambda x: x["timestamp"], reverse=True)
    print(f"   - 👍 Đã lấy và sắp xếp xong. Tổng cộng có {len(sorted_articles)} bài viết.")
    return sorted_articles

def load_existing_translations():
    """Đọc file news.json hiện có và tạo một từ điển các bản dịch."""
    print("\n---\n📖 Đang tải các bản dịch đã có từ `news.json`...")
    if not os.path.exists("news.json"):
        print("   - ⚠️ Không tìm thấy file `news.json`. Bắt đầu với bộ nhớ đệm trống.")
        return {}
    try:
        with open("news.json", "r", encoding="utf-8") as f:
            news_data = json.load(f)
            translations = {item['title_zh']: item['title_vi'] for item in news_data if 'title_zh' in item and 'title_vi' in item}
            print(f"   - ✅ Đã tải thành công {len(translations)} bản dịch.")
            return translations
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"   - ❌ Lỗi khi đọc `news.json`: {e}. Bắt đầu với bộ nhớ đệm trống.")
        return {}

# -- MAIN --
if __name__ == "__main__":
    print("🚀 Bắt đầu chạy script cập nhật tin tức...")
    
    translations = load_existing_translations()
    articles = fetch_all_albums(ALBUMS)

    all_zh_titles = [a["title"] for a in articles]
    titles_to_translate = [title for title in all_zh_titles if title not in translations]

    print(f"   - 📊 Tổng hợp: Đã tải {len(translations)} bản dịch, phát hiện {len(titles_to_translate)} tiêu đề mới.")

    print("\n---\n🌐 Bắt đầu quá trình dịch thuật...")
    if titles_to_translate:
        print(f"   - Tìm thấy {len(titles_to_translate)} tiêu đề mới cần dịch.")
        newly_translated_titles = batch_translate_zh_to_vi(titles_to_translate)

        print("   - Cập nhật bộ nhớ đệm bản dịch...")
        for zh_title, vi_title in zip(titles_to_translate, newly_translated_titles):
            translations[zh_title] = vi_title
        print("   - ✅ Đã cập nhật xong.")
    else:
        print("   - ✅ Không có tiêu đề mới nào cần dịch. Tất cả đều đã có trong bộ nhớ đệm.")

    news_list = []
    print("\n---\n✍️  Bắt đầu tạo danh sách tin tức cuối cùng...")
    for article in articles:
        zh_title = article["title"]
        vi_title = translations.get(zh_title, zh_title)

        if re.search(r'[\u4e00-\u9fff]', vi_title) and vi_title == zh_title:
            print(f"   - ⚠️  Xử lý (chưa dịch): {zh_title[:50]}...")
        else:
            print(f"   - ✔️  Xử lý (đã dịch): {vi_title[:50]}...")

        news_list.append({
            "title_zh": zh_title,
            "title_vi": vi_title,
            "url": article["url"],
            "cover_img": article["cover_img"],
            "date": article["date"]
        })
    print("   - 👍 Đã xử lý xong tất cả các bài viết.")

    print("\n---\n💾 Đang ghi dữ liệu vào `news.json`...")
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print("   - ✅ Đã ghi thành công.")
    print("\n🎉 Hoàn tất! Script đã chạy xong.")
