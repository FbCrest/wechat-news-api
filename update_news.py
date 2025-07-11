import requests
from bs4 import BeautifulSoup
import json

from vertexai.language_models import ChatModel

# Initialize Gemini model
chat_model = ChatModel.from_pretrained("chat-bison")
chat = chat_model.start_chat()

def fetch_news():
    url = "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzU5NjU1NjY1Mw==&action=getalbum&album_id=3447004682407854082"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    news_list = []
    for item in soup.find_all("div", class_="album__item"):
        title_tag = item.find("h3")
        link_tag = item.find("a")
        if title_tag and link_tag:
            title_cn = title_tag.get_text(strip=True)
            link = link_tag["href"]
            news_list.append({"title_cn": title_cn, "url": link})
    return news_list

def translate_title_gemini(title_cn):
    prompt = f"Hãy dịch tiêu đề này sang tiếng Việt:\n{title_cn}"
    response = chat.send_message(prompt)
    return response.text.strip()

def save_json(news_list):
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    print("Tải bài viết...")
    raw_news = fetch_news()
    print(f"Tìm thấy {len(raw_news)} bài.")
    translated_news = []
    for i, item in enumerate(raw_news, start=1):
        print(f"Dịch bài {i}/{len(raw_news)}...")
        try:
            vi_title = translate_title_gemini(item["title_cn"])
        except Exception as e:
            print("Lỗi dịch:", e)
            vi_title = item["title_cn"]
        translated_news.append({
            "title_cn": item["title_cn"],
            "title_vi": vi_title,
            "url": item["url"]
        })
    print("Lưu news.json...")
    save_json(translated_news)
    print("Hoàn tất!")
