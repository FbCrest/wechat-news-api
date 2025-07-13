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
    """
    Dịch một batch các đoạn text. Nếu gặp lỗi quota (429), trả về None để báo cho main dừng lại.
    """
    joined_titles = "\n".join(titles)
    prompt = (
        "Bạn là một chuyên gia dịch thuật tiếng Trung - Việt, có hiểu biết sâu sắc về game mobile Trung Quốc, đặc biệt là 'Nghịch Thủy Hàn Mobile'.\n"
        "Hãy dịch tất cả các đoạn sau sang **tiếng Việt tự nhiên, súc tích, đúng văn phong giới game thủ Việt**, giữ thứ tự dòng.\n\n"
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
        elif response.status_code == 429:
            print("❌ Lỗi: Vượt quá quota dịch của Gemini API (429). Đã dừng toàn bộ quá trình dịch. Vui lòng kiểm tra quota hoặc thử lại sau.")
            return None
        elif response.status_code == 503:
            print(f"⚠️ Mô hình quá tải. Thử lại lần {attempt + 1}/{retries} sau {delay}s...")
            time.sleep(delay)
        else:
            print(f"❌ Lỗi dịch ({response.status_code}):", response.text)
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
    for i in range(0, len(articles), batch_size):
        batch_titles = all_titles[i:i+batch_size]
        batch_contents = all_contents[i:i+batch_size]
        print(f"\n🌐 Đang dịch batch tiêu đề {i+1}-{i+len(batch_titles)}...")
        vi_batch_titles = batch_translate_zh_to_vi(batch_titles)
        if vi_batch_titles is None:
            quota_exceeded = True
            break
        vi_titles.extend(vi_batch_titles)
        time.sleep(2)  # delay nhỏ giữa các batch
        print(f"🌐 Đang dịch batch nội dung {i+1}-{i+len(batch_contents)}...")
        vi_batch_contents = batch_translate_zh_to_vi(batch_contents)
        if vi_batch_contents is None:
            quota_exceeded = True
            break
        vi_contents.extend(vi_batch_contents)
        time.sleep(2)

    if quota_exceeded:
        print("\n❌ Đã dừng toàn bộ quá trình dịch do vượt quota. news.json sẽ chứa nội dung gốc (chưa dịch)!")

    for idx, article in enumerate(articles):
        vi_title = vi_titles[idx] if idx < len(vi_titles) else article["title"]
        vi_content = vi_contents[idx] if idx < len(vi_contents) else all_contents[idx]
        if re.search(r'[\u4e00-\u9fff]', vi_title) or re.search(r'[\u4e00-\u9fff]', vi_content):
            print(f"⚠️ Bài {idx+1}: Dịch chưa hoàn chỉnh!")
        print(f"➡️ {vi_title}")
        news_list.append({
            "title_zh": article["title"],
            "title_vi": vi_title,
            "content_zh": all_contents[idx],
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
