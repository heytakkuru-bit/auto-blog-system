"""
自動ブログ投稿スクリプト
  - 100キーワード（3カテゴリ）から順番に記事生成
  - Gemini API で タイトル・本文・タグを自動生成
  - 投稿済み記事への内部リンクを自動挿入
  - WordPress REST API で投稿
  - 1日3回（設定時刻）に自動投稿
"""

import logging
import os
import sys
import time
from pathlib import Path

import schedule
from dotenv import load_dotenv

import re

from article_generator import ArticleGenerator
from wordpress_poster import WordPressPoster
from image_generator import ImageGenerator
from product_generator import ProductGenerator
from product_seller import ProductSeller
from internal_link_manager import (
    PublishedArticle,
    find_related,
    format_links_for_prompt,
    save_article,
)
import keyword_manager
from article_generator import HOBBY_CATEGORY

load_dotenv(Path(__file__).parent / ".env")

HOBBY_INTERVAL = 6   # この投稿数ごとに1回番外編を混ぜる
RETRY_COUNT = 3      # 失敗時のリトライ回数
RETRY_WAIT = 600     # リトライ間隔（秒）= 10分

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent / "auto_blog.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def _pick_next_entry(pending):
    """投稿済み件数に応じて次のキーワードを選ぶ。6件に1件は番外編。"""
    from internal_link_manager import load_all
    total_posted = len(load_all())
    use_hobby = (total_posted + 1) % HOBBY_INTERVAL == 0

    hobby = [e for e in pending if e.category == HOBBY_CATEGORY]
    regular = [e for e in pending if e.category != HOBBY_CATEGORY]

    if use_hobby and hobby:
        logger.info(f"[HOBBY] {total_posted + 1}件目 → 番外編を選択")
        return hobby[0]
    if use_hobby and not hobby:
        logger.info("[HOBBY] 番外編キーワード残なし → 通常記事にフォールバック")
    if regular:
        return regular[0]
    return pending[0]  # 通常キーワードも尽きた場合は先頭


def _attach_product(article: dict) -> dict:
    """
    記事に対応するプロンプト集を生成し、販売ページを作成して
    記事末尾に CTA バナーを追加した article dict を返す。
    失敗しても記事投稿は止めないよう例外を握り潰す。
    """
    try:
        gen = ProductGenerator()
        product = gen.generate(article)

        seller = ProductSeller()
        media = seller.upload_file(product["filepath"])
        if not media:
            logger.warning("[PRODUCT] Media upload failed, skipping sales page")
            return article

        page = seller.create_sales_page(product, media, article["title"])
        if not page:
            logger.warning("[PRODUCT] Sales page creation failed, skipping CTA")
            return article

        cta = seller.build_cta_html(product["title"], page.get("link", ""))
        article = dict(article)
        article["content"] = article["content"] + cta
        logger.info(f"[PRODUCT] CTA attached: {page.get('link')}")
    except Exception as e:
        logger.error(f"[PRODUCT] Workflow failed (article will still post): {e}", exc_info=True)
    return article


def _attach_images(article: dict, keyword: str, poster: WordPressPoster) -> dict:
    """
    記事内の <!-- IMAGE:type:description --> マーカーを実画像に置換し、
    最初の画像をアイキャッチとして設定する。
    失敗しても記事投稿は止めない。
    """
    pattern = re.compile(r'<!-- IMAGE:(\w+):([^>]+?) -->')
    if os.getenv("ENABLE_IMAGES", "false").lower() != "true":
        article = dict(article)
        article["content"] = pattern.sub("", article["content"])
        return article

    max_images = int(os.getenv("IMAGE_MAX_PER_ARTICLE", "2"))
    markers = pattern.findall(article["content"])
    if not markers:
        return article

    try:
        gen = ImageGenerator()
    except Exception as e:
        logger.warning(f"[IMAGE] ImageGenerator init failed: {e}")
        return article

    article = dict(article)
    inserted = 0

    def replace_marker(m: re.Match) -> str:
        nonlocal inserted
        if inserted >= max_images:
            return ""
        img_type, description = m.group(1), m.group(2).strip()
        prompt = ImageGenerator.build_prompt(keyword, description)
        img_bytes = gen.generate(prompt)
        if not img_bytes:
            return ""
        slug = re.sub(r"[^a-z0-9]", "-", keyword.lower())[:30]
        filename = f"{slug}-{img_type}-{inserted + 1}.png"
        media_id, media_url = poster.upload_media(img_bytes, filename)
        if not media_url:
            return ""
        inserted += 1
        if inserted == 1 and not article.get("featured_media_id"):
            article["featured_media_id"] = media_id
        alt = description[:60]
        return (
            f'<figure style="text-align:center;margin:28px 0;">'
            f'<img src="{media_url}" alt="{alt}" '
            f'style="max-width:100%;border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,0.12);">'
            f'<figcaption style="color:#777;font-size:0.88em;margin-top:8px;">'
            f'{alt}</figcaption></figure>'
        )

    article["content"] = pattern.sub(replace_marker, article["content"])
    logger.info(f"[IMAGE] {inserted} image(s) attached")
    return article


def post_one_article() -> bool:
    pending = keyword_manager.load_pending()
    if not pending:
        logger.warning("No pending keywords. Resetting used list.")
        keyword_manager.reset_used()
        pending = keyword_manager.load_pending()
        if not pending:
            logger.error("keywords.txt is empty.")
            return False

    entry = _pick_next_entry(pending)
    keyword = entry.keyword
    category = entry.category

    try:
        # 内部リンク候補を取得
        related = find_related(keyword, category)
        links_prompt = format_links_for_prompt(related)

        # 記事生成
        generator = ArticleGenerator()
        article = generator.generate(keyword, category, links_prompt)

        # デジタル商材の自動生成（番外編記事はスキップ）
        if os.getenv("ENABLE_PRODUCT", "true").lower() == "true" and category != HOBBY_CATEGORY:
            article = _attach_product(article)

        # 画像生成・アップロード
        poster = WordPressPoster()
        article = _attach_images(article, keyword, poster)

        # WordPress投稿
        result = poster.post(article)

        # 投稿済みDBに保存
        save_article(PublishedArticle(
            keyword=keyword,
            category=category,
            title=article["title"],
            url=result.get("link", ""),
            wp_id=result.get("id", 0),
        ))

        keyword_manager.mark_used(keyword)
        logger.info(f"[SUCCESS] '{keyword}' -> {result.get('link')}")
        return True

    except Exception as e:
        logger.error(f"[FAILED] '{keyword}': {e}", exc_info=True)
        return False


def run_daily_posts() -> None:
    logger.info("=== Starting daily batch (3 articles) ===")
    results = [post_one_article() for _ in range(3)]
    logger.info(f"=== Done: {sum(results)}/3 articles posted ===")


def show_status() -> None:
    pending = keyword_manager.load_pending()
    all_entries = keyword_manager._read_keywords(keyword_manager.KEYWORD_FILE)
    used = len(all_entries) - len(pending)

    from internal_link_manager import load_all
    published = load_all()

    print(f"\n--- 進捗状況 ---")
    print(f"総キーワード数 : {len(all_entries)}")
    print(f"投稿済み       : {used}")
    print(f"残り           : {len(pending)}")
    print(f"published DB   : {len(published)} 件")

    from collections import Counter
    cat_counts = Counter(e.category for e in pending)
    print("\nカテゴリ別残り:")
    for cat, cnt in cat_counts.most_common():
        print(f"  {cat}: {cnt}件")
    print()


def post_with_retry() -> bool:
    """失敗時に最大RETRY_COUNT回、RETRY_WAIT秒間隔でリトライする。"""
    for attempt in range(1, RETRY_COUNT + 1):
        if post_one_article():
            return True
        if attempt < RETRY_COUNT:
            logger.warning(f"Retry {attempt}/{RETRY_COUNT - 1}: waiting {RETRY_WAIT // 60} min...")
            time.sleep(RETRY_WAIT)
    logger.error("All retry attempts failed.")
    return False


def setup_schedule() -> None:
    post_times = os.getenv("POST_TIMES", "08:00,13:00,20:00").split(",")
    for t in [s.strip() for s in post_times]:
        schedule.every().day.at(t).do(post_with_retry)
        logger.info(f"Scheduled: {t}")


def main() -> None:
    args = sys.argv[1:]

    if "run-now" in args:
        run_daily_posts()
    elif "post-one" in args:
        success = post_one_article()
        sys.exit(0 if success else 1)
    elif "verify" in args:
        try:
            ok = WordPressPoster().verify_connection()
            sys.exit(0 if ok else 1)
        except Exception as e:
            logger.error(e)
            sys.exit(1)
    elif "status" in args:
        show_status()
    else:
        logger.info("Starting scheduler mode...")
        setup_schedule()
        logger.info("Scheduler running. Press Ctrl+C to stop.")
        while True:
            schedule.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    main()
