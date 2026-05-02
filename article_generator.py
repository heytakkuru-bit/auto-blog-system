import os
import time
import logging
from google import genai
from google.genai import types
from google.genai.errors import ClientError

logger = logging.getLogger(__name__)

# 優先順に試すモデル一覧（クォータ超過時に次を試す）
MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]


class ArticleGenerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=api_key)
        self.language = os.getenv("ARTICLE_LANGUAGE", "Japanese")
        self.min_chars = int(os.getenv("ARTICLE_MIN_CHARS", "1500"))

    def generate(self, keyword: str, category: str = "", related_links_prompt: str = "") -> dict:
        logger.info(f"Generating article for keyword: {keyword} [{category}]")
        prompt = self._build_prompt(keyword, category, related_links_prompt)

        last_error = None
        for model in MODELS:
            try:
                logger.info(f"Trying model: {model}")
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.8,
                        max_output_tokens=8192,
                    ),
                )
                return self._parse_response(response.text, keyword, category)
            except ClientError as e:
                if e.code == 429:
                    logger.warning(f"Quota exceeded for {model}, trying next model...")
                    last_error = e
                    time.sleep(2)
                    continue
                raise

        raise last_error or RuntimeError("All Gemini models failed")

    def _build_prompt(self, keyword: str, category: str, related_links_prompt: str) -> str:
        category_hint = f"カテゴリ: {category}\n" if category else ""
        internal_links_section = f"\n## 内部リンク指示\n{related_links_prompt}\n" if related_links_prompt else ""

        return f"""
あなたはSEOに精通したプロのブログライターです。
以下のキーワードに関する高品質な記事を{self.language}で書いてください。

キーワード: {keyword}
{category_hint}{internal_links_section}
## 記事の要件
- 読者ターゲット: 初心者〜中級者
- 文字数: {self.min_chars}文字以上
- 構成: 導入（課題提起）→ 本文（具体的な手順・解説）→ まとめ（行動喚起）
- SEOを意識し、キーワードを自然に本文に含める
- 具体的な手順や例文、テンプレートがあれば積極的に含める

## 出力フォーマット（マーカーは必ず含めること）

===TITLE===
（SEOを意識した魅力的なタイトル。32〜40文字が理想。数字や「方法」「テンプレ」などを含めると効果的）
===END_TITLE===

===EXCERPT===
（120〜160文字の記事概要。メタディスクリプションとして使用。キーワードを含め、クリックしたくなる文章に）
===END_EXCERPT===

===TAGS===
（記事に関連するタグを5〜8個、カンマ区切りで。例: ChatGPT,プロンプト,AI活用,業務効率化）
===END_TAGS===

===CONTENT===
（HTML形式の本文。以下のルールを守ること:
  - 見出しは <h2>、<h3> タグを使用
  - 箇条書きは <ul><li> タグ、番号付きリストは <ol><li> タグ
  - 重要な語句は <strong> タグで強調
  - テンプレートや例文は <pre><code> タグまたは <blockquote> タグで囲む
  - 内部リンクは指示がある場合、<a href="URL">アンカーテキスト</a> 形式で自然に挿入
  - 各セクションは読みやすく、空行を適切に入れる）
===END_CONTENT===
"""

    def _parse_response(self, text: str, keyword: str, category: str) -> dict:
        def extract(marker: str) -> str:
            start = text.find(f"==={marker}===")
            end = text.find(f"===END_{marker}===")
            if start == -1 or end == -1:
                return ""
            return text[start + len(f"==={marker}==="):end].strip()

        title = extract("TITLE") or f"{keyword}の完全ガイド【テンプレ付き】"
        excerpt = extract("EXCERPT") or ""
        tags_raw = extract("TAGS") or ""
        content = extract("CONTENT") or text.strip()

        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        logger.info(f"Generated: title='{title}' chars={len(content)} tags={tags}")
        return {
            "title": title,
            "excerpt": excerpt,
            "content": content,
            "tags": tags,
            "keyword": keyword,
            "category": category,
        }
