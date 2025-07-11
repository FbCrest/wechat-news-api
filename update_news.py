import requests
from bs4 import BeautifulSoup
from googletrans import Translator
import json

def fetch_news():
    url = "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzU5NjU1NjY1Mw==&action=getalbum&album_id=3447004682407854082"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
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

def translate_titles(news_list):
    translator = Translator()
    result = []
    for item in news_list:
        try:
            trans = translator.translate(item["title_cn"], src='zh-cn', dest='vi')
            title_vi = trans.text
        except Exception as e:
            print(f"Lỗi dịch: {e}")
            title_vi = item["title_cn"]
        result.append({
            "title_cn": item["title_cn"],
            "title_vi": title_vi,
            "url": item["url"]
        })
    return result

def save_json(news_list):
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    print("Bắt đầu tải bài viết...")
    raw_news = fetch_news()
    print(f"Tìm thấy {len(raw_news)} bài viết.")
    print("Bắt đầu dịch sang tiếng Việt...")
    translated_news = translate_titles(raw_news)
    print("Lưu file news.json...")
    save_json(translated_news)
    print("Hoàn tất!")
