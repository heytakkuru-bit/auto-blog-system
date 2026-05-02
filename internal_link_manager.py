"""
投稿済み記事を published_articles.json で管理し、
新規記事に挿入すべき内部リンク候補を返す。
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List

logger = logging.getLogger(__name__)

DB_FILE = Path(__file__).parent / "published_articles.json"
MAX_LINKS = 5  # 1記事あたりの内部リンク上限


@dataclass
class PublishedArticle:
    keyword: str
    category: str
    title: str
    url: str
    wp_id: int


def load_all() -> List[PublishedArticle]:
    if not DB_FILE.exists():
        return []
    data = json.loads(DB_FILE.read_text(encoding="utf-8"))
    return [PublishedArticle(**d) for d in data]


def save_article(article: PublishedArticle) -> None:
    all_articles = load_all()
    # 同じ wp_id があれば上書き
    all_articles = [a for a in all_articles if a.wp_id != article.wp_id]
    all_articles.append(article)
    DB_FILE.write_text(
        json.dumps([asdict(a) for a in all_articles], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"Saved article to DB: {article.title} ({article.url})")


def find_related(keyword: str, category: str) -> List[PublishedArticle]:
    """
    関連記事を優先度順に返す:
    1. 同カテゴリ & キーワードのトークンが重複
    2. 同カテゴリ
    3. その他（異カテゴリでトークン重複）
    """
    all_articles = load_all()
    kw_tokens = set(keyword.split())

    def score(a: PublishedArticle) -> int:
        a_tokens = set(a.keyword.split())
        overlap = len(kw_tokens & a_tokens)
        same_cat = 2 if a.category == category else 0
        return overlap * 3 + same_cat

    scored = [(score(a), a) for a in all_articles if a.keyword != keyword]
    scored.sort(key=lambda x: -x[0])

    results = [a for _, a in scored if _ > 0][:MAX_LINKS]
    logger.info(f"Found {len(results)} related articles for '{keyword}'")
    return results


def format_links_for_prompt(related: List[PublishedArticle]) -> str:
    if not related:
        return ""
    lines = ["以下の記事は既にサイトに存在します。本文中の適切な箇所に自然な形で内部リンクとして挿入してください（<a href=\"URL\">アンカーテキスト</a> 形式）:"]
    for a in related:
        lines.append(f'- タイトル: {a.title}  URL: {a.url}')
    return "\n".join(lines)
