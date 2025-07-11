import requests
import json

WECHAT_URL = "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzU5NjU1NjY1Mw==&album_id=3447004682407854082&f=json"

if __name__ == "__main__":
    print("🔍 Đang test phản hồi JSON...")
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(WECHAT_URL, headers=headers)
    print("✅ Mã HTTP:", resp.status_code)
    print("💡 Nội dung trả về:")
    print(resp.text)
