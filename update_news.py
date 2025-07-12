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

def translate_html_content_zh_to_vi(html_content, retries=3, delay=20):
    """Dịch nội dung HTML, giữ nguyên thẻ, với cơ chế thử lại và xử lý lỗi rate limit."""
    if not html_content or not html_content.strip():
        return ""

    headers = {"Content-Type": "application/json"}
    prompt = (
        "You are an expert translator. Your task is to translate the text content within the following HTML snippet from Chinese to Vietnamese.\n"
        "**Crucially, you must preserve all HTML tags and their structure exactly as they are.**\n"
        "Only translate the user-visible text. Do not translate attribute values like src, href, class, id, etc.\n"
        "The content is from a gaming news article. Keep game-related terms in English or use common Vietnamese equivalents.\n\n"
        f"Original HTML:\n{html_content}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "topP": 0.95,
            "topK": 40
        }
    }

    for attempt in range(retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=180)
            if response.status_code == 200:
                result = response.json()
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
                cleaned_html = raw_text.strip().removeprefix('```html').removesuffix('```').strip()
                print("    ✅ Dịch HTML thành công.")
                return cleaned_html
            elif response.status_code in [429, 503]:
                wait_time = delay * (attempt + 1)
                print(f"    ⚠️ Lỗi {response.status_code} (Quá tải/Giới hạn). Thử lại lần {attempt + 1}/{retries} sau {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    ❌ Lỗi không mong muốn khi dịch HTML: {response.status_code} - {response.text}")
                return ""  # Trả về chuỗi rỗng khi có lỗi nghiêm trọng
        except requests.exceptions.RequestException as e:
            print(f"    ❌ Lỗi mạng khi dịch HTML: {e}. Thử lại sau {delay}s...")
            time.sleep(delay)

    print("    ❌ Thử lại nhiều lần nhưng vẫn lỗi. Bỏ qua dịch HTML.")
    return ""

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
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        author_element = soup.select_one('#js_name')
        author = author_element.text.strip() if author_element else 'N/A'

        content_div = soup.select_one('#js_content')
        if not content_div:
            return None

        # Remove script tags
        for script in content_div.find_all('script'):
            script.decompose()

        html_content = str(content_div)
        images = [img.get('data-src', img.get('src')) for img in content_div.find_all('img') if img.get('data-src') or img.get('src')]

        return {
            'author': author,
            'html_content': html_content,
            'images': images
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching article details from {url}: {e}")
        return None
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
    # B1: Tải cache từ news.json nếu có
    existing_news = {}
    if os.path.exists("news.json"):
        try:
            with open("news.json", "r", encoding="utf-8") as f:
                old_news_list = json.load(f)
                for item in old_news_list:
                    if item.get("url"):
                        existing_news[item["url"]] = item
            print(f"✅ Đã tải {len(existing_news)} bài viết từ cache.")
        except (json.JSONDecodeError, FileNotFoundError):
            print("⚠️ Không thể đọc file cache news.json, sẽ tạo mới từ đầu.")
            existing_news = {}

    # B2: Lấy danh sách bài viết mới nhất từ các album
    articles = fetch_all_albums(ALBUMS)

    # B3: Dịch tiêu đề hàng loạt (vẫn hiệu quả)
    zh_titles = [a["title"] for a in articles]
    print("\n🌐 Đang dịch tất cả tiêu đề...")
    vi_titles = batch_translate_zh_to_vi(zh_titles)

    # B4: Xử lý từng bài viết
    final_news_list = []
    for i, article_summary in enumerate(articles):
        print(f"\n[{i+1}/{len(articles)}] Đang xử lý: {article_summary['title']}")
        article_url = article_summary['url']

        # Kiểm tra cache: Nếu bài viết đã có và đã được dịch thì dùng lại
        cached_article = existing_news.get(article_url)
        if cached_article and cached_article.get("html_content_vi"):
            print("    ➡️  Đã có bản dịch trong cache, bỏ qua.")
            # Cập nhật thông tin mới nhất như tiêu đề, ngày đăng
            cached_article['title_vi'] = vi_titles[i] if i < len(vi_titles) else cached_article.get('title_vi', '')
            cached_article['date'] = article_summary['date']
            final_news_list.append(cached_article)
            continue

        # Dịch tiêu đề
        vi_title = vi_titles[i] if i < len(vi_titles) else article_summary["title"]
        print(f"    ➡️  Tiêu đề VI: {vi_title}")

        # Lấy chi tiết bài viết
        print("    ↪️  Đang tải chi tiết bài viết...")
        details = fetch_article_details(article_url)
        if not details:
            print(f"    ❌ Không thể tải chi tiết cho: {article_summary['title']}")
            continue

        # Dịch nội dung HTML
        print("    ↪️  Đang dịch nội dung HTML...")
        translated_html = translate_html_content_zh_to_vi(details['html_content'])

        # Nếu dịch thất bại, không thêm vào danh sách cuối cùng
        if not translated_html:
            print(f"    ❌ Dịch nội dung thất bại, bỏ qua bài viết này.")
            continue

        # Tạo đối tượng bài viết hoàn chỉnh
        full_article_data = {
            "title_zh": article_summary["title"],
            "title_vi": vi_title,
            "url": article_url,
            "cover_img": article_summary["cover_img"],
            "date": article_summary["date"],
            "author": details.get("author", "Không rõ"),
            "html_content_vi": translated_html,
            "images": details.get("images", [])
        }
        final_news_list.append(full_article_data)

        # Thêm độ trễ 5 giây để tránh rate limit
        print("    ⏳ Tạm nghỉ 5 giây để tránh quá tải API...")
        time.sleep(5)

    # B5: Sắp xếp lại danh sách cuối cùng theo timestamp để đảm bảo thứ tự
    final_news_list.sort(key=lambda x: existing_news.get(x['url'], {}).get('timestamp', 0) if 'timestamp' in existing_news.get(x['url'], {}) else [a for a in articles if a['url'] == x['url']][0]['timestamp'], reverse=True)

    # B6: Lưu kết quả
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(final_news_list, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! Đã tạo file news.json với cơ chế cache và chống quá tải.")
