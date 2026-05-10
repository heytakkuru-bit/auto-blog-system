"""
デジタル商材の販売ページ自動作成モジュール
- WordPress メディアライブラリへのファイルアップロード
- パスワード保護付き販売ページの自動作成
- 記事末尾 CTA HTML の生成
"""
import io
import os
import re
import base64
import logging
import zipfile
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
        self.price_take  = os.getenv("PRODUCT_PRICE", "300")
        self.price_matsu = os.getenv("PRODUCT_PRICE_MATSU", "3000")
        self.password    = os.getenv("PRODUCT_PASSWORD", "teqsnap2026")
        self.thanks_url  = os.getenv("THANKS_PAGE_URL", "")
        # 竹: STRIPE_PAYMENT_URL_TAKE → STRIPE_PAYMENT_URL の順で参照
        self.stripe_url_take  = (os.getenv("STRIPE_PAYMENT_URL_TAKE")
                                 or os.getenv("STRIPE_PAYMENT_URL", ""))
        self.stripe_url_matsu = os.getenv("STRIPE_PAYMENT_URL_MATSU", "")
        # 後方互換
        self.stripe_url = self.stripe_url_take

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
        """ファイルを ZIP 化して WordPress メディアライブラリにアップロードする"""
        # サーバーの WAF が .txt を弾くため ZIP に変換してアップロード
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(filepath, arcname=filepath.name)
        zip_bytes = buf.getvalue()

        safe_stem = re.sub(r"[^\x00-\x7F]", "_", filepath.stem)
        zip_name = f"{safe_stem}.zip"

        resp = requests.post(
            self._api_url("/media"),
            data=zip_bytes,
            headers={
                "Authorization": self.auth_header,
                "Content-Disposition": f'attachment; filename="{zip_name}"',
                "Content-Type": "application/zip",
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
            f"① 下の「Stripeで購入する」ボタンからお支払い（{self.price_take}円）<br>"
            f"② 決済完了後、パスワードが表示されます<br>"
            f"③ このページに戻ってパスワードを入力するとダウンロードできます</p>"
            f"</div>"
            f'<p style="text-align:center;">'
            f'<a href="{self.stripe_url}" target="_blank" rel="noopener" '
            f'style="display:inline-block;background:#635bff;color:white;'
            f'padding:14px 32px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:16px;">'
            f"Stripeで購入する（{self.price_take}円）</a></p>"
            f"<h3>ダウンロード</h3>"
            f'<p><a href="{download_url}" download '
            f'style="display:inline-block;background:#3b5bdb;color:white;'
            f'padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold;">'
            f"プロンプト集をダウンロード（ZIP）</a></p>"
            f"<p><small>ZIP を解凍するとテキストファイルが入っています。メモ帳などで開けます。</small></p>"
        )

    def build_cta_html(self, product_title: str, sales_page_url: str) -> str:
        """記事末尾に挿入する CTA バナー HTML（竹メイン＋松サブ）を返す"""
        take_url  = self.stripe_url_take  or sales_page_url
        matsu_url = self.stripe_url_matsu or ""

        matsu_block = ""
        if matsu_url:
            matsu_block = (
                f'<div style="margin-top:16px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.3);">'
                f'<p style="font-size:12px;margin:0 0 8px;opacity:0.85;">もっと本気でAIを使いこなしたいなら</p>'
                f'<a href="{matsu_url}" target="_blank" rel="noopener" '
                f'style="display:inline-block;background:rgba(255,255,255,0.15);color:white;'
                f'border:2px solid white;padding:9px 24px;border-radius:6px;font-weight:bold;'
                f'text-decoration:none;font-size:14px;">【松】フルサポートセット（{self.price_matsu}円）</a>'
                f'<p style="font-size:11px;margin:6px 0 0;opacity:0.65;">全記事プロンプト集 + 個別チャット相談1回</p>'
                f'</div>'
            )
        else:
            matsu_block = (
                f'<div style="margin-top:16px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.3);">'
                f'<p style="font-size:11px;margin:0;opacity:0.6;">🚀 近日公開：【松】フルサポートセット（{self.price_matsu}円）— 個別相談付き</p>'
                f'</div>'
            )

        return (
            f'<div style="background:linear-gradient(135deg,#3b5bdb,#7048e8);'
            f'color:white;padding:28px 24px;border-radius:12px;margin:40px 0;text-align:center;font-family:sans-serif;">'
            f'<p style="font-size:11px;margin:0 0 4px;opacity:0.75;letter-spacing:0.05em;">この記事の作業をAIで一瞬で終わらせる</p>'
            f'<p style="font-size:20px;font-weight:bold;margin:0 0 8px;">{product_title}</p>'
            f'<p style="font-size:12px;margin:0 0 18px;opacity:0.85;">'
            f'実戦プロンプト3選 ✅ 2026年動作確認済み ✅ コピペで即使える</p>'
            f'<a href="{take_url}" target="_blank" rel="noopener" '
            f'style="display:inline-block;background:white;color:#3b5bdb;'
            f'padding:13px 32px;border-radius:8px;font-weight:bold;text-decoration:none;font-size:16px;">'
            f'【竹】今すぐ購入（{self.price_take}円）</a>'
            f'<p style="margin:8px 0 0;font-size:11px;opacity:0.6;">'
            f'クレジットカード決済 / 購入直後にダウンロード可能</p>'
            f'{matsu_block}'
            f'</div>'
        )
