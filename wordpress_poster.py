from __future__ import annotations
import os
import base64
import logging
from pathlib import Path
from typing import Optional, List
import requests

logger = logging.getLogger(__name__)


class WordPressPoster:
    def __init__(self):
        self.url = os.getenv("WP_URL", "").rstrip("/")
        # http → https に正規化（リダイレクト先に合わせる）
        if self.url.startswith("http://"):
            self.url = "https://" + self.url[len("http://"):]

        username = os.getenv("WP_USERNAME", "")
        app_password = os.getenv("WP_APP_PASSWORD", "")

        if not all([self.url, username, app_password]):
            raise ValueError("WP_URL, WP_USERNAME, WP_APP_PASSWORD are required")

        token = base64.b64encode(f"{username}:{app_password}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }
        self.api_base = self._detect_api_base()
        self._static_featured_id = None

    def _detect_api_base(self) -> str:
        """REST APIのベースURLを判定する。pretty permalink を優先し、最大2回試みる。"""
        pretty = f"{self.url}/wp-json/wp/v2"
        fallback = f"{self.url}?rest_route=/wp/v2"

        for attempt in range(2):
            try:
                resp = requests.get(f"{self.url}/wp-json/", timeout=10, allow_redirects=True)
                if resp.ok and "routes" in resp.text:
                    logger.info(f"API base (pretty): {pretty}")
                    return pretty
            except Exception:
                pass

        logger.info(f"API base (fallback): {fallback}")
        return fallback

    def get_static_featured_media_id(self) -> Optional[int]:
        if self._static_featured_id:
            return self._static_featured_id

        try:
            resp = requests.get(
                self._api_url("/media"),
                params={"search": "gorilla-mascot", "per_page": 5},
                headers=self.headers,
                timeout=10,
            )
            if resp.ok:
                for item in resp.json():
                    source_url = item.get("source_url", "")
                    title = item.get("title", {}).get("rendered", "").lower()
                    if source_url.endswith("gorilla-mascot.png") or "gorilla" in title:
                        self._static_featured_id = item.get("id")
                        return self._static_featured_id
        except Exception as e:
            logger.warning(f"Static featured lookup failed: {e}")

        local_path = Path(__file__).parent / "assets" / "gorilla-mascot.png"
        if local_path.exists():
            try:
                with open(local_path, "rb") as f:
                    image_bytes = f.read()
                media_id, _ = self.upload_media(image_bytes, local_path.name)
                self._static_featured_id = media_id
                return self._static_featured_id
            except Exception as e:
                logger.error(f"Static featured upload failed: {e}")
        else:
            logger.error(f"Static gorilla image missing: {local_path}")
        return None

    def _api_url(self, path: str) -> str:
        """エンドポイントURLを組み立てる。fallback形式に対応。"""
        if "rest_route" in self.api_base:
            # ?rest_route=/wp/v2 → ?rest_route=/wp/v2/posts
            base_route = self.api_base.split("rest_route=")[1]
            return f"{self.url}?rest_route={base_route}{path}"
        return f"{self.api_base}{path}"

    def upload_media(self, image_bytes: bytes, filename: str = "header.png") -> Optional[int]:
        """画像をWordPressメディアライブラリにアップロードしてmedia IDを返す。"""
        headers = {
            "Authorization": self.headers["Authorization"],
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/png",
        }
        try:
            resp = requests.post(
                self._api_url("/media"),
                headers=headers,
                data=image_bytes,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Media uploaded: id={data.get('id')} url={data.get('source_url')}")
            return data.get("id"), data.get("source_url")
        except Exception as e:
            logger.warning(f"Media upload failed: {e}")
            return None, None

    def post(self, article: dict, status: str = "publish") -> dict:
        category_id = self._get_or_create_category(article.get("category", ""))
        tag_ids = self._get_or_create_tags(article.get("tags", []))

        payload = {
            "title": article["title"],
            "content": article["content"],
            "excerpt": article.get("excerpt", ""),
            "status": status,
            "format": "standard",
        }
        if category_id:
            payload["categories"] = [category_id]
        if tag_ids:
            payload["tags"] = tag_ids
        if article.get("featured_media_id"):
            payload["featured_media"] = article["featured_media_id"]
        else:
            static_id = self.get_static_featured_media_id()
            if static_id:
                payload["featured_media"] = static_id

        logger.info(f"Posting: '{article['title']}'")
        response = requests.post(
            self._api_url("/posts"), json=payload, headers=self.headers, timeout=30
        )
        response.raise_for_status()

        result = response.json()
        logger.info(f"Posted: id={result.get('id')} url={result.get('link')}")
        return result

    def _get_or_create_category(self, category_name: str) -> Optional[int]:
        if not category_name:
            return None

        resp = requests.get(
            self._api_url("/categories"),
            params={"search": category_name, "per_page": 1},
            headers=self.headers,
            timeout=10,
        )
        if resp.ok and resp.json():
            return resp.json()[0]["id"]

        create = requests.post(
            self._api_url("/categories"),
            json={"name": category_name},
            headers=self.headers,
            timeout=10,
        )
        return create.json().get("id") if create.ok else None

    def _get_or_create_tags(self, tag_names: List[str]) -> List[int]:
        ids = []
        for name in tag_names:
            resp = requests.get(
                self._api_url("/tags"),
                params={"search": name, "per_page": 1},
                headers=self.headers,
                timeout=10,
            )
            if resp.ok and resp.json():
                ids.append(resp.json()[0]["id"])
                continue

            create = requests.post(
                self._api_url("/tags"),
                json={"name": name},
                headers=self.headers,
                timeout=10,
            )
            if create.ok:
                ids.append(create.json()["id"])
        return ids

    def update_post(self, wp_id: int, article: dict) -> dict:
        """既存の投稿をタイトル・本文・アイキャッチで上書きする。"""
        payload = {
            "title": article["title"],
            "content": article["content"],
            "excerpt": article.get("excerpt", ""),
        }
        if article.get("featured_media_id"):
            payload["featured_media"] = article["featured_media_id"]
        else:
            static_id = self.get_static_featured_media_id()
            if static_id:
                payload["featured_media"] = static_id

        logger.info(f"Updating post id={wp_id}: '{article['title']}'")
        response = requests.post(
            self._api_url(f"/posts/{wp_id}"),
            json=payload,
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Updated: id={result.get('id')} url={result.get('link')}")
        return result

    def verify_connection(self) -> bool:
        try:
            resp = requests.get(
                self._api_url("/users/me"), headers=self.headers, timeout=10
            )
            if resp.status_code == 401:
                data = resp.json()
                logger.error(f"認証失敗: {data.get('message')} (code: {data.get('code')})")
                return False
            resp.raise_for_status()
            logger.info(f"WordPress connected as: {resp.json().get('name')}")
            return True
        except Exception as e:
            logger.error(f"WordPress connection failed: {e}")
            return False
