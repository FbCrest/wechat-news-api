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

def has_chinese_chars(s):
    """Kiểm tra xem chuỗi có chứa ký tự tiếng Trung hay không."""
    return re.search(r'[\u4e00-\u9fff]', s)

def translate_plain_text_zh_to_vi(text, retries=3, delay=25):
    """Dịch văn bản thuần túy, với cơ chế thử lại và xác thực kết quả."""
    if not text or not text.strip():
        return ""

    headers = {"Content-Type": "application/json"}
    prompt = (
        "Bạn là một chuyên gia dịch thuật tiếng Trung - Việt, chuyên về game 'Nghịch Thủy Hàn Mobile'.\n"
        "Hãy dịch nội dung sau sang tiếng Việt một cách tự nhiên, chính xác, giữ nguyên các dấu xuống dòng.\n"
        "Không thêm bất kỳ bình luận, ghi chú hay lời chào nào.\n\n"
        f"Nội dung cần dịch:\n{text}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4}
    }

    for attempt in range(retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
            if response.status_code == 200:
                result = response.json()
                translated_text = result["candidates"][0]["content"]["parts"][0]["text"]
                
                # Xác thực kết quả: nếu vẫn còn tiếng Trung, coi như thất bại
                if has_chinese_chars(translated_text) and len(translated_text) > len(text) * 0.5:
                    print(f"    ⚠️ Dịch có vẻ thất bại (còn tiếng Trung). Thử lại lần {attempt + 1}/{retries}...")
                    time.sleep(delay * (attempt + 1))
                    continue # Bỏ qua và thử lại

                print("    ✅ Dịch văn bản thành công.")
                return fix_terms(translated_text)
            elif response.status_code in [429, 503]:
                wait_time = delay * (attempt + 1)
                print(f"    ⚠️ Lỗi {response.status_code}. Thử lại sau {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    ❌ Lỗi dịch: {response.status_code} - {response.text}")
                # Không trả về chuỗi rỗng ngay, thử lại ở lần tiếp theo
                time.sleep(delay * (attempt + 1))

        except requests.exceptions.RequestException as e:
            print(f"    ❌ Lỗi mạng khi dịch: {e}. Thử lại sau {delay}s...")
            time.sleep(delay)

    print(f"    ❌ Thử lại nhiều lần nhưng vẫn lỗi. Trả về văn bản gốc cho: '{text[:30]}...' ")
    return text # Trả về văn bản gốc nếu dịch thất bại hoàn toàn

def batch_translate_zh_to_vi(text_blocks, retries=3, delay=20, chunk_char_limit=5000):
    """Dịch hàng loạt, hỗ trợ chia nhỏ khối văn bản dài và xác thực kết quả."""
    if not text_blocks:
        return []

    # --- Logic chia nhỏ (Chunking) ---
    chunks = []
    current_chunk = []
    current_length = 0
    for block in text_blocks:
        if current_length + len(block) > chunk_char_limit and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_length = 0
        current_chunk.append(block)
        current_length += len(block)
    if current_chunk:
        chunks.append(current_chunk)
    
    all_translated_blocks = []
    for i, chunk in enumerate(chunks):
        print(f"    📦 Đang dịch gói {i + 1}/{len(chunks)} ({len(chunk)} khối văn bản)..._ ")
        translated_chunk = _translate_chunk(chunk, retries, delay)
        if translated_chunk:
            all_translated_blocks.extend(translated_chunk)
        else:
            # Nếu một gói bị lỗi, trả về toàn bộ văn bản gốc để đảm bảo tính toàn vẹn
            print("    ❌ Một gói dịch bị lỗi, sẽ giữ lại toàn bộ văn bản gốc cho bài viết này.")
            return text_blocks 

    return all_translated_blocks

def _translate_chunk(chunk, retries=3, delay=20):
    """Hàm phụ, dịch một gói văn bản duy nhất."""
    joined_text = "\n".join(chunk)
    prompt = (
        "Bạn là một chuyên gia dịch thuật tiếng Trung - Việt, chuyên về game 'Nghịch Thủy Hàn Mobile'.\n"
        "Hãy dịch các đoạn văn bản sau sang tiếng Việt. Mỗi đoạn được phân tách bằng dấu xuống dòng.\n"
        "**YÊU CẦU TUYỆT ĐỐI:**\n"
        "1. **DỊCH TOÀN BỘ:** Không được bỏ sót bất kỳ câu, từ hay chi tiết nào.\n"
        "2. **GIỮ NGUYÊN SỐ LƯỢNG:** Phải trả về chính xác cùng số lượng đoạn văn như đã nhận.\n"
        "3. **KHÔNG THÊM THẮT:** Không thêm bình luận, ghi chú, hay định dạng không cần thiết.\n\n"
        f"CÁC ĐOẠN CẦN DỊCH:\n{joined_text}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4}
    }

    for attempt in range(retries):
        try:
            response = requests.post(API_URL, headers={"Content-Type": "application/json"}, json=payload, timeout=180)
            if response.status_code == 200:
                result = response.json()
                if not result.get('candidates') or not result['candidates'][0].get('content'):
                    print(f"    ⚠️ Phản hồi API không hợp lệ. Thử lại lần {attempt + 1}/{retries}...")
                    time.sleep(delay * (attempt + 1))
                    continue

                translated_text = result['candidates'][0]['content']['parts'][0]['text']
                translated_blocks = [fix_terms(line.strip()) for line in translated_text.split('\n') if line.strip()]
                
                if len(translated_blocks) != len(chunk):
                    print(f"    ⚠️ Số lượng dòng trả về ({len(translated_blocks)}) không khớp ({len(chunk)}). Thử lại...")
                    time.sleep(delay * (attempt + 1))
                    continue

                if any(has_chinese_chars(t) for t in translated_blocks):
                    print(f"    ⚠️ Kết quả dịch vẫn chứa tiếng Trung. Thử lại lần {attempt + 1}/{retries}...")
                    time.sleep(delay * (attempt + 1))
                    continue

                print(f"    ✅ Dịch gói thành công và đã xác thực.")
                return translated_blocks

            elif response.status_code in [429, 503]:
                wait_time = delay * (attempt + 1)
                print(f"    ⚠️ Lỗi {response.status_code}. Thử lại sau {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    ❌ Lỗi dịch: {response.status_code} - {response.text}")
                time.sleep(delay * (attempt + 1))
        except requests.exceptions.RequestException as e:
            print(f"    ❌ Lỗi mạng khi dịch: {e}")
            time.sleep(delay)

    print(f"    ❌ Dịch gói thất bại sau nhiều lần thử.")
    return None # Trả về None nếu thất bại

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
    """Bóc tách bài viết thành các khối văn bản và hình ảnh có cấu trúc."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        content_div = soup.find('div', id='js_content')
        if not content_div:
            return None

        structured_content = []
        # Lặp qua tất cả các thẻ con trực tiếp trong div nội dung
        for element in content_div.find_all(recursive=False):
            # Tìm tất cả ảnh trong element hiện tại
            images_in_element = element.find_all('img')
            text_in_element = element.get_text(strip=True)

            if images_in_element:
                for img in images_in_element:
                    img_src = img.get('data-src') or img.get('src')
                    if img_src:
                        structured_content.append({'type': 'image', 'url': img_src})
            elif text_in_element:
                # Chỉ thêm khối văn bản nếu nó có nội dung
                structured_content.append({'type': 'text', 'content': text_in_element})

        return {
            'structured_content': structured_content
        }
    except requests.exceptions.RequestException as e:
        print(f"    ❌ Lỗi khi tải chi tiết bài viết: {e}")
        return None
    except Exception as e:
        print(f"    ❌ Lỗi không xác định khi xử lý chi tiết bài viết: {e}")
        return None

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
    existing_news_map = {}
    if os.path.exists("news.json"):
        try:
            with open("news.json", "r", encoding="utf-8") as f:
                old_news_list = json.load(f)
                for item in old_news_list:
                    if item.get("url"):
                        existing_news_map[item["url"]] = item
            print(f"✅ Đã tải {len(existing_news_map)} bài viết từ cache.")
        except (json.JSONDecodeError, FileNotFoundError):
            print("⚠️ Không thể đọc file cache news.json, sẽ tạo mới từ đầu.")
            existing_news_map = {}

    # B2: Lấy danh sách bài viết mới nhất từ các album
    articles_from_source = fetch_all_albums(ALBUMS)

    # B3: Lọc thông minh: Xác định bài mới, bài cần dịch lại, và bài đã hoàn chỉnh
    articles_to_process = []
    final_news = []
    print("\n🔎 Bắt đầu lọc và phân loại bài viết...")
    for article in articles_from_source:
        url = article['url']
        if url not in existing_news_map:
            print(f"  - [MỚI] {article['title']}")
            articles_to_process.append(article)
        else:
            cached_article = existing_news_map[url]
            is_title_translated = 'title_vi' in cached_article and cached_article['title_vi'] and not has_chinese_chars(cached_article['title_vi'])
            
            is_content_translated = True
            if 'structured_content_vi' in cached_article and cached_article['structured_content_vi']:
                for block in cached_article['structured_content_vi']:
                    if block['type'] == 'text' and has_chinese_chars(block['content']):
                        is_content_translated = False
                        break
            else:
                is_content_translated = False

            if not is_title_translated or not is_content_translated:
                print(f"  - [DỊCH LẠI] {article['title']}")
                articles_to_process.append(article)
            else:
                # Bài đã dịch hoàn chỉnh, giữ lại từ cache nhưng cập nhật ngày
                cached_article['date'] = article['date']
                final_news.append(cached_article)

    print(f"\n=> 📊 Tổng cộng có {len(articles_to_process)} bài viết cần xử lý.")

    # B4: Xử lý các bài viết cần thiết
    if articles_to_process:
        for i, article_summary in enumerate(articles_to_process):
            print(f"\n[{i+1}/{len(articles_to_process)}] Đang xử lý: {article_summary['title']}")
            article_url = article_summary['url']

            # Dịch tiêu đề (dịch đơn lẻ để đảm bảo chính xác)
            print("    ➡️  Đang dịch tiêu đề...")
            vi_title = translate_plain_text_zh_to_vi(article_summary["title"])
            print(f"    ➡️  Tiêu đề VI: {vi_title}")

            # Lấy chi tiết bài viết (chỉ khi cần dịch nội dung)
            print("    ↪️  Đang tải và phân tích nội dung...")
            details = fetch_article_details(article_url)
            if not details:
                print(f"    ❌ Không thể tải chi tiết cho: {article_summary['title']}")
                continue

            # Tách và dịch các khối văn bản
            text_blocks_to_translate = [block['content'] for block in details['structured_content'] if block['type'] == 'text' and block['content'].strip()]
            if text_blocks_to_translate:
                translated_blocks = batch_translate_zh_to_vi(text_blocks_to_translate)
                if len(translated_blocks) == len(text_blocks_to_translate):
                    # Ghép lại nội dung đã dịch vào cấu trúc
                    translated_content_iterator = iter(translated_blocks)
                    for block in details['structured_content']:
                        if block['type'] == 'text' and block['content'].strip():
                            block['content'] = next(translated_content_iterator)
                else:
                    print(f"    ❌ Dịch nội dung thất bại, số khối trả về không khớp. Sẽ giữ lại nội dung gốc.")
            
            # Tạo đối tượng bài viết hoàn chỉnh
            full_article_data = {
                "title_zh": article_summary["title"],
                "title_vi": vi_title,
                "url": article_url,
                "cover_img": article_summary["cover_img"],
                "date": article_summary["date"],
                "structured_content_vi": details['structured_content']
            }
            final_news.append(full_article_data)
            print(f"    ✅ Đã xử lý xong: {vi_title}")
            time.sleep(10) # Nghỉ giữa các bài viết

    # B5: Kết hợp và lưu kết quả cuối cùng
    # Sắp xếp lại danh sách cuối cùng theo timestamp gốc để đảm bảo thứ tự
    url_to_timestamp = {a['url']: a['timestamp'] for a in articles_from_source}
    final_news.sort(key=lambda x: url_to_timestamp.get(x['url'], 0), reverse=True)

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(final_news, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! File news.json đã được cập nhật với logic cache thông minh.")
