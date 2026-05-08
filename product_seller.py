"""
デジタル商材の販売ページ自動作成モジュール
- WordPress メディアライブラリへのファイルアップロード
- パスワード保護付き販売ページの自動作成
- 記事末尾 CTA HTML の生成
"""
import os
import base64
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)


class ProductSeller:
    def __init__(self):
        wp_url = os.getenv("WP_URL", "").rstrip("/")
        if wp_url.startswith("http://"):
            wp_url = "https://" + wp_url[len("http://"):]

        username = os.getenv("WP_USERNAME", "")
        app_password = os.getenv("WP_APP_PASSWORD", "")

        token = base64.b64encode(f"{username}:{app_password}".encode()).decode()
        self.auth_header = f"Basic {token}"
        self.headers_json = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
        }
        self.wp_url = wp_url
        self.api_base = self._detect_api_base()
        self.price = os.getenv("PRODUCT_PRICE", "300")
        self.password = os.getenv("PRODUCT_PASSWORD", "teqsnap2026")

    def _detect_api_base(self) -> str:
        try:
            resp = requests.get(f"{self.wp_url}/wp-json/", timeout=8)
            if resp.ok and "routes" in resp.text:
                return f"{self.wp_url}/wp-json/wp/v2"
        except Exception:
            pass
        return f"{self.wp_url}?rest_route=/wp/v2"

    def _api_url(self, path: str) -> str:
        if "rest_route" in self.api_base:
            base_route = self.api_base.split("rest_route=")[1]
            return f"{self.wp_url}?rest_route={base_route}{path}"
        return f"{self.api_base}{path}"

    def upload_file(self, filepath: Path) -> dict:
        """.md ファイルを WordPress メディアライブラリにアップロードする"""
        with open(filepath, "rb") as f:
            file_content = f.read()

        resp = requests.post(
            self._api_url("/media"),
            data=file_content,
            headers={
                "Authorization": self.auth_header,
                "Content-Disposition": f'attachment; filename="{filepath.name}"',
                "Content-Type": "text/plain; charset=utf-8",
            },
            timeout=30,
        )

        if not resp.ok:
            logger.error(f"Media upload failed: {resp.status_code} {resp.text[:200]}")
            return {}

        result = resp.json()
        logger.info(f"File uploaded: {result.get('source_url')}")
        return result

    def create_sales_page(self, product: dict, media: dict, article_title: str) -> dict:
        """パスワード保護付き販売ページを作成する"""
        download_url = media.get("source_url", "")

        content = self._build_sales_page_content(
            product, download_url, article_title
        )

        resp = requests.post(
            self._api_url("/pages"),
            json={
                "title": product["title"],
                "content": content,
                "status": "publish",
                "password": self.password,
            },
            headers=self.headers_json,
            timeout=30,
        )

        if not resp.ok:
            logger.error(f"Sales page creation failed: {resp.status_code} {resp.text[:200]}")
            return {}

        result = resp.json()
        logger.info(f"Sales page created: {result.get('link')}")
        return result

    def _build_sales_page_content(
        self, product: dict, download_url: str, article_title: str
    ) -> str:
        return (
            f"{product['description']}"
            f"<hr>"
            f"<h3>購入・ダウンロード方法</h3>"
            f'<div style="background:#f0f4ff;border-left:4px solid #3b5bdb;padding:16px;margin:16px 0;border-radius:4px;">'
            f"<p><strong>このページはパスワード保護されています。</strong><br>"
            f"パスワードの取得方法：<a href='/contact'>お問い合わせフォーム</a>より"
            f"「{article_title}のプロンプト集購入希望」とお送りください。<br>"
            f"確認後、{self.price}円のお支払い方法をご案内します。"
            f"お支払い確認後にパスワードをお送りします。</p>"
            f"</div>"
            f"<h3>ダウンロード</h3>"
            f'<p><a href="{download_url}" download '
            f'style="display:inline-block;background:#3b5bdb;color:white;'
            f'padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold;">'
            f"プロンプト集をダウンロード</a></p>"
            f"<p><small>テキストエディタ（メモ帳など）で開けます</small></p>"
        )

    def build_cta_html(self, product_title: str, sales_page_url: str) -> str:
        """記事末尾に挿入する CTA バナー HTML を返す"""
        return (
            f'<div style="background:linear-gradient(135deg,#3b5bdb,#7048e8);'
            f"color:white;padding:24px;border-radius:12px;margin:32px 0;text-align:center;"
            f'font-family:sans-serif;">'
            f'<p style="font-size:13px;margin:0 0 6px;opacity:0.85;">'
            f"この記事の作業をAIで一瞬で終わらせる</p>"
            f'<p style="font-size:19px;font-weight:bold;margin:0 0 10px;">'
            f"{product_title}</p>"
            f'<p style="font-size:12px;margin:0 0 16px;opacity:0.8;">'
            f"実戦プロンプト3選 ✅ 2026年動作確認済み ✅ コピペで即使える</p>"
            f'<a href="{sales_page_url}" '
            f'style="display:inline-block;background:white;color:#3b5bdb;'
            f"padding:11px 28px;border-radius:6px;font-weight:bold;"
            f'text-decoration:none;font-size:15px;">'
            f"{self.price}円で購入する</a>"
            f'<p style="margin:10px 0 0;font-size:11px;opacity:0.65;">'
            f"お問い合わせよりご購入手続きができます</p>"
            f"</div>"
        )
