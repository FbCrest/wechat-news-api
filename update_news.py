import requests
import json
import os
import re
from datetime import datetime

# -- Cấu hình --
API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-1.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY}"

# -- Album nguồn --
ALBUMS = [
    "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzU5NjU1NjY1Mw==&album_id=3447004682407854082&f=json",
    "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzkyMjc1NzEzOA==&album_id=3646379824391471108&f=json",
    "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzI1MDQ1MjUxNw==&album_id=3664489989179457545&f=json"
]

# -- Bảng từ chuyên ngành cố định --
GLOSSARY = {
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

def cleanup(text):
    text = re.sub(r"\*\*.*?\*\*", "", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()

def fix_terms(text):
    for zh, vi in GLOSSARY.items():
        text = text.replace(zh, vi)
    return text

def call_gemini(prompt):
    headers = {"Content-Type": "application/json"}
    payload = { "contents": [ { "parts": [ { "text": prompt } ] } ] }
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        print("❌ Lỗi Gemini:", response.status_code)
        return None

def batch_translate_titles(titles):
    prompt = (
        "Bạn là một chuyên gia dịch thuật tiếng Trung - Việt, có hiểu biết sâu sắc về game mobile Trung Quốc, đặc biệt là 'Nghịch Thủy Hàn Mobile'.\n"
        "Hãy dịch tất cả các tiêu đề sau sang **tiếng Việt tự nhiên, súc tích, đúng văn phong giới game thủ Việt**, mang màu sắc hấp dẫn, ưu tiên giữ nguyên các thuật ngữ kỹ thuật, tên vật phẩm, và cấu trúc tiêu đề gốc.\n\n"
        "⚠️ Quy tắc dịch:\n"
        "- Giữ nguyên các cụm số (như 10W, 288).\n"
        "- Giữ nguyên tên kỹ năng, vũ khí, tính năng trong dấu [] hoặc 【】.\n"
        "- Ưu tiên từ ngữ phổ biến trong cộng đồng game như: 'build', 'phối đồ', 'đập đồ', 'lộ trình', 'trang bị xịn', 'ngoại hình đỉnh', 'top server'...\n"
        "- Các từ cố định phải dịch đúng theo bảng sau:\n"
        + "\n".join([f"- {zh} = {vi}" for zh, vi in GLOSSARY.items()]) +
        "\n\n🚫 Không được thêm bất kỳ ghi chú, số thứ tự, hoặc phần mở đầu.\n"
        "Chỉ dịch từng dòng tương ứng với danh sách sau:\n\n"
        + "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles)])
    )
    text = call_gemini(prompt)
    if not text: return titles
    return [fix_terms(line.strip()) for line in cleanup(text).split("\n") if line.strip()]

def translate_full_article(content):
    prompt = (
        "Bạn là một biên tập viên chuyên dịch nội dung game mobile Trung Quốc sang tiếng Việt.\n"
        "Hãy dịch nội dung bài viết sau sang **tiếng Việt rõ ràng, tự nhiên, đúng ngữ cảnh** như thể đang viết bài đăng chính thức cho fanpage game “Nghịch Thủy Hàn Mobile”.\n\n"
        "⚠️ Quy tắc bắt buộc:\n"
        "- Không để sót hoặc giữ lại tiếng Trung gốc.\n"
        "- Không thêm bất kỳ chú thích hay phần giới thiệu không có trong bài gốc.\n"
        "- Dùng giọng văn dễ hiểu, gần gũi, mang phong cách truyền thông game.\n"
        "⚠️ Quy tắc dịch:\n"
        "- Giữ nguyên các cụm số (như 10W, 288).\n"
        "- Giữ nguyên tên kỹ năng, vũ khí, tính năng trong dấu [] hoặc 【】.\n"
        "- Ưu tiên từ ngữ phổ biến trong cộng đồng game như: 'build', 'phối đồ', 'đập đồ', 'lộ trình', 'trang bị xịn', 'ngoại hình đỉnh', 'top server'...\n"
        "- Các từ cố định phải dịch đúng theo bảng sau:\n"
        + "\n".join([f"- {zh} = {vi}" for zh, vi in GLOSSARY.items()]) +
        "\n\n🚫 Tuyệt đối không sử dụng từ ngữ cứng nhắc kiểu máy dịch. Không dịch thô kiểu \"người chơi có thể tiến hành nhận\", hãy viết: \"game thủ có thể nhận\", hoặc \"bạn có thể nhận\"...\n\n"
        "Dưới đây là nội dung cần dịch:\n"
        "---\n" + content
    )
    result = call_gemini(prompt)
    return fix_terms(cleanup(result)) if result else ""

def fetch_articles(album_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(album_url, headers=headers)
    data = r.json()
    items = []
    for a in data.get("getalbum_resp", {}).get("article_list", []):
        timestamp = int(a.get("create_time", 0))
        dt = datetime.utcfromtimestamp(timestamp)
        weekday = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"][dt.weekday()]
        date_str = f"{dt.strftime('%H:%M')} - {weekday}, {dt.strftime('%d/%m')}"
        items.append({
            "title": a["title"],
            "url": a["url"],
            "cover_img": a.get("cover_img_1_1") or a.get("cover"),
            "timestamp": timestamp,
            "date": date_str
        })
    return sorted(items, key=lambda x: x["timestamp"], reverse=True)[:4]

def fetch_all_articles():
    all = []
    for url in ALBUMS:
        all.extend(fetch_articles(url))
    return sorted(all, key=lambda x: x["timestamp"], reverse=True)

def save_article_html(file_id, title, date, content, cover):
    os.makedirs("news_articles", exist_ok=True)
    path = f"news_articles/{file_id}.html"
    content_html = content.replace('\n', '<br>')
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <link href="https://fonts.googleapis.com/css2?family=Roboto&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; }}
    h1 {{ color: #00ffaa; }}
    .date {{ color: #999; font-size: 14px; margin-bottom: 20px; }}
    img.cover {{ max-width: 100%; border-radius: 10px; margin: 20px 0; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="date">{date}</div>
  <img class="cover" src="{cover}" alt="Cover">
  <div>{content_html}</div>
</body>
</html>""")

if __name__ == "__main__":
    print("🔍 Đang lấy bài viết từ các album...")
    articles = fetch_all_articles()
    zh_titles = [a["title"] for a in articles]

    print("\n🌐 Đang dịch tiêu đề...")
    vi_titles = batch_translate_titles(zh_titles)

    news_json = []
    for i, art in enumerate(articles):
        title_vi = vi_titles[i] if i < len(vi_titles) else art["title"]
        article_id = str(art["timestamp"])
        print(f"📄 [{i+1}] {title_vi}")

        try:
            resp = requests.get(art["url"], headers={"User-Agent": "Mozilla/5.0"})
            html = resp.text
            content_match = re.search(
    r'<div class="rich_media_content[^>]*?>(.*?)</div>\s*<div class="rich_media_area_extra"',
    html,
    re.S
)
            content_html = content_match.group(1) if content_match else ""
            content_text = re.sub("<.*?>", "", content_html)
            content_text = re.sub(r"\s{2,}", " ", content_text.strip())

            print("📝 Đang dịch bài viết...")
            translated = translate_full_article(content_text)

            save_article_html(article_id, title_vi, art["date"], translated, art["cover_img"])
        except Exception as e:
            print("⚠️ Lỗi xử lý nội dung:", e)
            continue

        news_json.append({
            "title_zh": art["title"],
            "title_vi": title_vi,
            "url": f"news_articles/{article_id}.html",
            "cover_img": art["cover_img"],
            "date": art["date"]
        })

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_json, f, ensure_ascii=False, indent=2)

    print("\n🎉 Hoàn tất! File news.json + HTML đã được tạo.")
