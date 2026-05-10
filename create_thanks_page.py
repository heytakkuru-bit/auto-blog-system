"""
サンクスページをWordPressに作成するスクリプト。
決済完了後のリダイレクト先として機能し、竹・松どちらの購入者にも対応。

使い方: python3 create_thanks_page.py
"""
import os, base64, logging
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WP_URL      = os.getenv("WP_URL", "").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "")
WP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")
WP_PAGE_PASSWORD = os.getenv("PRODUCT_PASSWORD", "teqsnap2026")

TOKEN   = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {TOKEN}", "Content-Type": "application/json"}
API     = f"{WP_URL}/wp-json/wp/v2"


THANKS_CONTENT = f"""
<div style="max-width:640px;margin:40px auto;font-family:sans-serif;text-align:center;">

  <div style="background:linear-gradient(135deg,#3b5bdb,#7048e8);color:white;padding:40px 32px;border-radius:16px;margin-bottom:32px;">
    <p style="font-size:48px;margin:0 0 12px;">🎉</p>
    <h1 style="color:white;font-size:26px;margin:0 0 8px;">購入ありがとうございます！</h1>
    <p style="opacity:0.9;margin:0;">脳筋タックルです。ほんまにありがとう！</p>
  </div>

  <div style="background:#f8f9fa;border-radius:12px;padding:28px;margin-bottom:24px;text-align:left;">
    <h2 style="font-size:18px;margin:0 0 16px;">📦 ダウンロード手順</h2>
    <ol style="margin:0;padding-left:20px;line-height:2.2;">
      <li>下のパスワードをコピーする</li>
      <li>購入した記事ページに戻る</li>
      <li>「プロンプト集を見る」ボタンを押してパスワードを入力</li>
      <li>ダウンロードボタンでテキストファイルを保存</li>
    </ol>
  </div>

  <div style="background:#e8f4fd;border:2px dashed #2196F3;border-radius:12px;padding:24px;margin-bottom:24px;">
    <p style="margin:0 0 8px;font-size:13px;color:#555;">ダウンロードパスワード</p>
    <p style="font-size:28px;font-weight:bold;color:#1565C0;letter-spacing:0.1em;margin:0;">{WP_PAGE_PASSWORD}</p>
    <p style="font-size:12px;color:#888;margin:8px 0 0;">このページをスクショしておくと便利です</p>
  </div>

  <div style="background:#e8f5e9;border-left:4px solid #4CAF50;padding:16px 20px;border-radius:0 8px 8px 0;text-align:left;margin-bottom:24px;">
    <strong style="color:#1B5E20;">💡 使い方のコツ</strong><br>
    プロンプトはChatGPT・Claude・Geminiどれでも使えます。まずコピペして、自分の状況に合わせて少しカスタムするのがコツやで！
  </div>

  <div style="border-top:1px solid #e0e0e0;padding-top:24px;color:#888;font-size:13px;">
    <p>【松】フルサポートセットにご興味の方は<br>
    <a href="https://teqsnap.com" style="color:#3b5bdb;">teqsnap.com</a> のお問い合わせからどうぞ</p>
    <p style="margin-top:16px;">— 脳筋タックル</p>
  </div>

</div>
"""


def create_or_update_thanks_page() -> str:
    # 既存ページ検索
    resp = requests.get(f"{API}/pages", params={"search": "ありがとう", "per_page": 5}, headers=HEADERS, timeout=10)
    pages = resp.json() if resp.ok else []
    existing = next((p for p in pages if "thanks" in p.get("slug", "") or "ありがとう" in p.get("title", {}).get("rendered", "")), None)

    payload = {
        "title":   "購入ありがとうございます！",
        "slug":    "thanks-95bb6f0c3e9c9ad2",
        "content": THANKS_CONTENT,
        "status":  "publish",
    }

    if existing:
        r = requests.post(f"{API}/pages/{existing['id']}", json=payload, headers=HEADERS, timeout=15)
        action = "更新"
    else:
        r = requests.post(f"{API}/pages", json=payload, headers=HEADERS, timeout=15)
        action = "作成"

    r.raise_for_status()
    url = r.json().get("link", "")
    logger.info(f"サンクスページ{action}: {url}")
    return url


if __name__ == "__main__":
    url = create_or_update_thanks_page()
    print(f"\n✅ サンクスページ: {url}")
