from __future__ import annotations
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

logger = logging.getLogger(__name__)

KEYWORD_FILE = Path(__file__).parent / "keywords.txt"
USED_FILE = Path(__file__).parent / "used_keywords.txt"


@dataclass
class KeywordEntry:
    keyword: str
    category: str


def load_pending() -> List[KeywordEntry]:
    all_entries = _read_keywords(KEYWORD_FILE)
    used = {e.keyword for e in _read_keywords(USED_FILE)}
    pending = [e for e in all_entries if e.keyword not in used]
    logger.info(f"Pending keywords: {len(pending)} / {len(all_entries)}")
    return pending


def mark_used(keyword: str) -> None:
    entry = _find_entry(keyword)
    category = entry.category if entry else "未分類"
    with open(USED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{keyword}\t{category}\n")
    logger.info(f"Marked as used: {keyword} [{category}]")


def reset_used() -> None:
    if USED_FILE.exists():
        USED_FILE.unlink()
    logger.info("Reset used keywords")


def get_category_keywords(category: str) -> List[KeywordEntry]:
    return [e for e in _read_keywords(KEYWORD_FILE) if e.category == category]


def _find_entry(keyword: str) -> Optional[KeywordEntry]:
    for e in _read_keywords(KEYWORD_FILE):
        if e.keyword == keyword:
            return e
    return None


def _read_keywords(path: Path) -> List[KeywordEntry]:
    if not path.exists():
        return []

    entries = []
    current_category = "未分類"

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[category:") and line.endswith("]"):
            current_category = line[len("[category:"):].rstrip("]").strip()
            continue
        # used_keywords.txt は "keyword\tcategory" 形式
        parts = line.split("\t", 1)
        keyword = parts[0].strip()
        category = parts[1].strip() if len(parts) > 1 else current_category
        if keyword:
            entries.append(KeywordEntry(keyword=keyword, category=category))

    return entries
