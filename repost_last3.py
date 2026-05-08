"""直近3投稿を新しいプロンプト・ビジュアルで再生成してWordPress記事を更新する。"""
import json
import logging
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from article_generator import ArticleGenerator
from wordpress_poster import WordPressPoster
from image_generator import ImageGenerator
from internal_link_manager import find_related, format_links_for_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

IMAGE_MAX = int(os.getenv("IMAGE_MAX_PER_ARTICLE", "2"))
ENABLE_IMAGES = os.getenv("ENABLE_IMAGES", "true").lower() == "true"


def attach_images(article: dict, keyword: str, poster: WordPressPoster) -> dict:
    if not ENABLE_IMAGES:
        return article
    pattern = re.compile(r'<!-- IMAGE:(\w+):([^>]+?) -->')
    if not pattern.search(article["content"]):
        return article
    try:
        gen = ImageGenerator()
    except Exception as e:
        logger.warning(f"[IMAGE] init failed: {e}")
        return article

    article = dict(article)
    inserted = 0

    def replace_marker(m: re.Match) -> str:
        nonlocal inserted
        if inserted >= IMAGE_MAX:
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
            f'<figcaption style="color:#777;font-size:0.88em;margin-top:8px;">{alt}</figcaption>'
            f'</figure>'
        )

    article["content"] = pattern.sub(replace_marker, article["content"])
    logger.info(f"[IMAGE] {inserted} image(s) attached")
    return article


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    data = json.load(open("published_articles.json"))
    targets = data[-n:]

    poster = WordPressPoster()
    generator = ArticleGenerator()
    ok = 0

    for entry in targets:
        wp_id    = entry["wp_id"]
        keyword  = entry["keyword"]
        category = entry["category"]
        logger.info(f"=== Reposting wp_id={wp_id} keyword='{keyword}' ===")

        try:
            related = find_related(keyword, category)
            links_prompt = format_links_for_prompt(related)
            article = generator.generate(keyword, category, links_prompt)
            article = attach_images(article, keyword, poster)
            poster.update_post(wp_id, article)
            logger.info(f"[OK] wp_id={wp_id} updated")
            ok += 1
        except Exception as e:
            logger.error(f"[FAIL] wp_id={wp_id}: {e}", exc_info=True)

    logger.info(f"=== Done: {ok}/{n} updated ===")
    sys.exit(0 if ok == n else 1)


if __name__ == "__main__":
    main()
