import requests
import json
import os
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

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
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
            clean_text = cleanup_translation(raw_text)
            lines = [fix_terms(line.strip()) for line in clean_text.split("\n") if line.strip()]
            return lines
        elif response.status_code == 503:
            print(f"⚠️ Mô hình quá tải. Thử lại lần {attempt + 1}/{retries} sau {delay}s...")
            time.sleep(delay)
        else:
            print("❌ Lỗi dịch:", response.status_code, response.text)
            return titles

    print("❌ Thử lại nhiều lần nhưng vẫn lỗi. Bỏ qua dịch.")
    return titles

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

def fetch_article_details(url):
    print(f"    ↪ Đang lấy chi tiết từ: {url[:40]}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Lấy tên tác giả/kênh
        author_element = soup.find('strong', class_='profile_nickname')
        author = author_element.get_text(strip=True) if author_element else "Không rõ"

        # Lấy nội dung chính
        content_element = soup.find('div', class_='rich_media_content')
        if not content_element:
            return {"error": "Không tìm thấy nội dung chính"}

        # Trích xuất HTML và text
        html_content = str(content_element)
        text_content = content_element.get_text('\n', strip=True)

        # Lấy tất cả hình ảnh, ưu tiên data-src cho ảnh lazy-load
        images = []
        for img in content_element.find_all('img'):
            src = img.get('data-src') or img.get('src')
            if src and src.startswith('http'):
                images.append(src)

        return {
            "author": author,
            "html_content": html_content,
            "text_content": text_content,
            "images": images
        }
    except requests.RequestException as e:
        print(f"    ❌ Lỗi khi lấy chi tiết bài viết: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"    ❌ Lỗi không xác định: {e}")
        return {"error": str(e)}

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
        print(f"\n[{i+1}/{len(articles)}] Đang xử lý: {article['title']}")
        
        # Dịch tiêu đề
        vi_title = vi_titles[i] if i < len(vi_titles) else article["title"]
        if re.search(r'[\u4e00-\u9fff]', vi_title):
            print(f"    ⚠️ Dịch tiêu đề chưa hoàn chỉnh!")
        print(f"    ➡️ Tiêu đề VI: {vi_title}")

        # Lấy chi tiết bài viết
        details = fetch_article_details(article['url'])
        if 'error' in details:
            print(f"    ❌ Bỏ qua bài viết do lỗi: {details['error']}")
            continue

        # Kết hợp thông tin
        full_article_data = {
            "title_zh": article["title"],
            "title_vi": vi_title,
            "url": article["url"],
            "cover_img": article["cover_img"],
            "date": article["date"],
            "author": details.get("author", "Không rõ"),
            "html_content": details.get("html_content", ""),
            "text_content": details.get("text_content", ""),
            "images": details.get("images", [])
        }
        news_list.append(full_article_data)

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! Đã tạo file news.json.")
