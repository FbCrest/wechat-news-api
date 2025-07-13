import requests
import json
import os
import re
import time
from datetime import datetime

# -- Cấu hình --
# Hỗ trợ nhiều API key Gemini (GEMINI_API_KEYS, ngăn cách bởi dấu phẩy)
API_KEYS = os.environ.get("GEMINI_API_KEYS")
if API_KEYS:
    GEMINI_API_KEYS = [k.strip() for k in API_KEYS.split(",") if k.strip()]
else:
    GEMINI_API_KEYS = [os.environ["GEMINI_API_KEY"]]
MODEL = "gemini-1.5-flash"
API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1/models/{}:generateContent?key={}".format(MODEL, "{}")

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

import concurrent.futures

def batch_translate_zh_to_vi_multi(texts, api_keys, retries=3, delay=10):
    """
    Dịch một danh sách văn bản, chia thành các batch nhỏ.
    Tự động phân phối cho các API key và thử lại với key khác nếu một key hết quota.
    """
    results = [None] * len(texts)
    batch_size = 3  # Dịch 3 mục mỗi lần để tránh quá tải
    untranslated_batches = list(enumerate([texts[i:i+batch_size] for i in range(0, len(texts), batch_size)]))
    active_key_indices = list(range(len(api_keys)))

    def translate_batch(batch, key_idx):
        api_key = api_keys[key_idx]
        api_url = API_URL_TEMPLATE.format(api_key)
        joined_texts = "\n".join(batch)
        prompt = (
            "Bạn là một chuyên gia dịch thuật tiếng Trung - Việt, có hiểu biết sâu sắc về game mobile Trung Quốc, đặc biệt là 'Nghịch Thủy Hàn Mobile'.\n"
            "Hãy dịch tất cả các đoạn sau sang **tiếng Việt tự nhiên, súc tích, đúng văn phong giới game thủ Việt**, giữ thứ tự dòng.\n\n"
            "⚠️ Quy tắc dịch:\n"
            "- Giữ nguyên các cụm số (như 10W, 288).\n"
            "- Giữ nguyên tên kỹ năng, vũ khí, tính năng trong dấu [] hoặc 【】.\n"
            "- Ưu tiên từ ngữ phổ biến trong cộng đồng game như: 'build', 'phối đồ', 'đập đồ', 'lộ trình', 'trang bị xịn', 'ngoại hình đỉnh', 'top server'...\n"
            "- Các từ cố định phải dịch đúng theo bảng sau:\n"
            "- 流 = lối chơi\n- 木桩 = cọc gỗ\n- 沧澜 = Thương Lan\n- 潮光 = Triều Quang\n- 玄机 = Huyền Cơ\n- 龙吟 = Long Ngâm\n- 神相 = Thần Tương\n- 血河 = Huyết Hà\n- 碎梦 = Toái Mộng\n- 素问 = Tố Vấn\n- 九灵 = Cửu Linh\n- 铁衣 = Thiết Y\n\n"
            "🚫 Không được thêm bất kỳ ghi chú, số thứ tự, hoặc phần mở đầu. Chỉ dịch từng dòng, giữ nguyên thứ tự gốc.\n\n"
            + joined_texts
        )
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=90)
            if response.status_code == 200:
                result = response.json()
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
                lines = [fix_terms(line.strip()) for line in cleanup_translation(raw_text).split('\n') if line.strip()]
                return lines, None
            elif response.status_code == 429:
                return None, "quota_exceeded"
            else:
                print(f"⚠️ Lỗi API không xác định với key {key_idx}. Status: {response.status_code}\n{response.text}")
                return None, "api_error"
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Lỗi kết nối với key {key_idx}: {e}")
            return None, "connection_error"

    while untranslated_batches and active_key_indices:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_key_indices)) as executor:
            future_to_batch = {}
            key_iterator = iter(active_key_indices)
            # Gửi các batch chưa dịch đi
            for batch_idx, batch_content in untranslated_batches:
                try:
                    key_idx = next(key_iterator)
                    future = executor.submit(translate_batch, batch_content, key_idx)
                    future_to_batch[future] = (batch_idx, batch_content, key_idx)
                except StopIteration:
                    break # Hết key để phân phối

            processed_batches = []
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_idx, batch_content, key_idx = future_to_batch[future]
                processed_batches.append((batch_idx, batch_content))
                try:
                    lines, error_type = future.result()
                    if lines:
                        start_pos = batch_idx * batch_size
                        results[start_pos:start_pos + len(lines)] = lines
                    elif error_type == "quota_exceeded":
                        print(f"🔑 Key {key_idx} hết quota. Loại bỏ khỏi danh sách hoạt động.")
                        if key_idx in active_key_indices:
                            active_key_indices.remove(key_idx)
                except Exception as exc:
                    print(f"❌ Batch {batch_idx} gây ra exception: {exc}")

            # Cập nhật danh sách các batch chưa dịch thành công
            all_processed_indices = {item[0] for item in processed_batches}
            untranslated_batches = [item for item in untranslated_batches if item[0] not in all_processed_indices]

    # Điền nội dung gốc cho các phần không dịch được
    for i, res in enumerate(results):
        if res is None:
            results[i] = texts[i]
            print(f"⚠️ Không dịch được mục {i}, sử dụng nội dung gốc.")

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

from bs4 import BeautifulSoup

def fetch_article_content(url):
    """
    Lấy nội dung text và hình ảnh từ một bài viết chi tiết trên WeChat.
    Trả về dict: {"content_text": ..., "images": [list link ảnh], "content_html": ...}
    """
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Referer": "https://mp.weixin.qq.com/",
    }
    resp = requests.get(url, headers=headers)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    # Nội dung chính nằm trong div id="js_content"
    content_div = soup.find("div", id="js_content")
    if not content_div:
        return {"content_text": "", "images": [], "content_html": ""}
    # Lấy text
    content_text = content_div.get_text("\n", strip=True)
    # Lấy html
    content_html = str(content_div)
    # Lấy link ảnh
    images = [img["data-src"] for img in content_div.find_all("img", attrs={"data-src": True})]
    return {"content_text": content_text, "images": images, "content_html": content_html}

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

    news_list = []
    batch_size = 6  # Dịch tối đa 6 bài/lần để tiết kiệm quota, có thể tăng/giảm tùy độ dài bài
    all_titles = []
    all_contents = []
    for article in articles:
        all_titles.append(article["title"])
        # Lấy nội dung bài viết trước, gom lại để dịch batch
        content_data = fetch_article_content(article["url"])
        all_contents.append(content_data["content_text"])
        article["_images"] = content_data["images"]  # tạm lưu images để dùng sau

    # Gom batch để dịch
    vi_titles = []
    vi_contents = []
    quota_exceeded = False
    print("\n🌐 Đang dịch tất cả tiêu đề...")
    vi_titles = batch_translate_zh_to_vi_multi(all_titles, GEMINI_API_KEYS)
    if vi_titles is None:
        print("\n❌ Đã dừng dịch do hết quota tất cả key. news.json sẽ chứa nội dung gốc!")
        vi_titles = all_titles
    time.sleep(2)
    print("🌐 Đang dịch tất cả nội dung...")
    vi_contents = batch_translate_zh_to_vi_multi(all_contents, GEMINI_API_KEYS)
    if vi_contents is None:
        print("\n❌ Đã dừng dịch do hết quota tất cả key. news.json sẽ chứa nội dung gốc!")
        vi_contents = all_contents
    time.sleep(2)

    for idx, article in enumerate(articles):
        raw_title = article["title"]
        raw_content = all_contents[idx]
        vi_title = vi_titles[idx] if idx < len(vi_titles) and vi_titles[idx] else raw_title
        vi_content = vi_contents[idx] if idx < len(vi_contents) and vi_contents[idx] else raw_content
        if re.search(r'[\u4e00-\u9fff]', vi_title) or re.search(r'[\u4e00-\u9fff]', vi_content):
            print(f"⚠️ Bài {idx+1}: Dịch chưa hoàn chỉnh!")
        print(f"➡️ {vi_title}")
        news_list.append({
            "title_zh": raw_title,
            "title_vi": vi_title,
            "content_zh": raw_content,
            "content_vi": vi_content,
            "url": article["url"],
            "cover_img": article["cover_img"],
            "images": article["_images"],
            "date": article["date"]
        })

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! Đã tạo file news.json với nội dung và hình ảnh.")

    # Render luôn news_full.html
    def render_news_html(news_json_path, output_html_path):
        with open(news_json_path, "r", encoding="utf-8") as f:
            news_list = json.load(f)

        html = [
            "<html>",
            "<head>",
            "<meta charset='utf-8'>",
            "<title>Tin tức dịch đầy đủ</title>",
            "<style>body{font-family:sans-serif;max-width:800px;margin:auto;background:#f7f7f7;}h1,h2{color:#2b4f81;}article{background:#fff;padding:24px 32px;margin:32px 0;border-radius:10px;box-shadow:0 2px 8px #0001;}img{max-width:100%;margin:16px 0;border-radius:6px;}</style>",
            "</head>",
            "<body>",
            "<h1>Tin tức dịch đầy đủ</h1>"
        ]
        for news in news_list:
            html.append("<article>")
            html.append(f"<h2>{news['title_vi']}</h2>")
            html.append(f"<div style='color:#888;font-size:14px;margin-bottom:8px'>{news['date']}</div>")
            if news.get("cover_img"):
                html.append(f"<img src='{news['cover_img']}' alt='cover' loading='lazy'>")
            # Nội dung bài viết
            html.append("<div style='white-space:pre-line;font-size:17px;line-height:1.7;margin:18px 0 0 0'>")
            html.append(news['content_vi'].replace("\n", "<br>"))
            html.append("</div>")
            # Ảnh trong bài
            if news.get("images"):
                for img_url in news["images"]:
                    html.append(f"<img src='{img_url}' alt='ảnh bài viết' loading='lazy'>")
            html.append("</article>")
        html.append("</body></html>")
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html))
        print(f"✅ Đã tạo {output_html_path}")

    render_news_html("news.json", "news_full.html")
