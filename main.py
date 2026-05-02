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

from article_generator import ArticleGenerator
from wordpress_poster import WordPressPoster
from internal_link_manager import (
    PublishedArticle,
    find_related,
    format_links_for_prompt,
    save_article,
)
import keyword_manager

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent / "auto_blog.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def post_one_article() -> bool:
    pending = keyword_manager.load_pending()
    if not pending:
        logger.warning("No pending keywords. Resetting used list.")
        keyword_manager.reset_used()
        pending = keyword_manager.load_pending()
        if not pending:
            logger.error("keywords.txt is empty.")
            return False

    entry = pending[0]
    keyword = entry.keyword
    category = entry.category

    try:
        # 内部リンク候補を取得
        related = find_related(keyword, category)
        links_prompt = format_links_for_prompt(related)

        # 記事生成
        generator = ArticleGenerator()
        article = generator.generate(keyword, category, links_prompt)

        # WordPress投稿
        poster = WordPressPoster()
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


def setup_schedule() -> None:
    post_times = os.getenv("POST_TIMES", "08:00,13:00,20:00").split(",")
    for t in [s.strip() for s in post_times]:
        schedule.every().day.at(t).do(post_one_article)
        logger.info(f"Scheduled: {t}")


def main() -> None:
    args = sys.argv[1:]

    if "run-now" in args:
        run_daily_posts()
    elif "post-one" in args:
        post_one_article()
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
