import os
import time
import logging
import httpx
import concurrent.futures
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

MODEL_TIMEOUT = 45  # 1モデルあたりの最大待ち時間（秒）

logger = logging.getLogger(__name__)

MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]

HOBBY_CATEGORY = "番外編・趣味ログ"


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
        is_hobby = category == HOBBY_CATEGORY
        if is_hobby:
            prompt = self._build_hobby_prompt(keyword, related_links_prompt)
        else:
            prompt = self._build_prompt(keyword, category, related_links_prompt)

        config = types.GenerateContentConfig(
            temperature=0.9 if is_hobby else 0.85,
            max_output_tokens=8192,
        )

        last_error = None
        for model in MODELS:
            try:
                logger.info(f"Trying model: {model}")
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(
                        self.client.models.generate_content,
                        model=model, contents=prompt, config=config,
                    )
                    try:
                        response = future.result(timeout=MODEL_TIMEOUT)
                    except concurrent.futures.TimeoutError:
                        logger.warning(f"Model {model} timed out ({MODEL_TIMEOUT}s), trying next...")
                        last_error = TimeoutError(f"{model} timed out")
                        continue
                return self._parse_response(response.text, keyword, category, is_hobby)
            except (ClientError, ServerError) as e:
                if e.code in (429, 503):
                    logger.warning(f"Model {model} unavailable ({e.code}), trying next...")
                    last_error = e
                    time.sleep(2)
                    continue
                raise
            except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(f"Model {model} network error ({type(e).__name__}), trying next...")
                last_error = e
                time.sleep(2)
                continue

        raise last_error or RuntimeError("All Gemini models failed")

    def _build_prompt(self, keyword: str, category: str, related_links_prompt: str) -> str:
        category_hint = f"カテゴリ: {category}\n" if category else ""
        internal_links_section = f"\n## 内部リンク指示\n{related_links_prompt}\n" if related_links_prompt else ""

        return f"""
あなたはSEOのプロでありながら、ユーモアと人間味を兼ね備えたブログライターです。
検索上位を狙いつつも、読んでいて「なるほど！」「わかる〜」「ちょっと笑えた」と思えるような記事を{self.language}で書いてください。
「SEOのために書いた感」が出ないよう、あくまで読者ファーストの自然な文章を心がけてください。

キーワード: {keyword}
{category_hint}{internal_links_section}
## SEO要件
- キーワードをタイトル・導入・見出し・本文に自然な形で含める
- 読者ターゲット: 初心者〜中級者
- 文字数: {self.min_chars}文字以上
- 構成: 導入（共感できる課題提起）→ 本文（具体的な手順・解説）→ まとめ（背中を押す一言）
- 具体的な手順や例文、テンプレートがあれば積極的に含める

## 文体・トーンの要件（重要）
- 導入は読者の悩みや「あるある」に寄り添う一言から始める（例:「〜って、最初は何が何だかわからないですよね」）
- SEOの専門知識をベースに、ところどころ軽いユーモアや本音トークを自然に挟む（例:「正直これだけやれば十分です（笑）」「よくある落とし穴なんですが、実は僕もやらかしました」）
- 読者に語りかける口調を保ちつつ、情報の信頼性・具体性は落とさない
- 「ちなみに」「実は」「意外と知られていないんですが」などのクッション言葉で専門知識をやわらかく伝える
- まとめは「難しく考えすぎず、まず一歩踏み出してみてください」など、読者の行動を後押しする温かいメッセージで締める

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

    def _build_hobby_prompt(self, keyword: str, related_links_prompt: str) -> str:
        internal_links_section = f"\n## 内部リンク指示\n{related_links_prompt}\n" if related_links_prompt else ""

        return f"""
あなたは「たっくる」という名前の、神奈川在住・アウトドア好きの20〜30代のブロガーです。
キャンプ・釣り・車中泊を趣味とし、経験から得た「知ってると得する豆知識」や「ハマってわかった通な情報」を発信するスタイルです。
特定の場所レポートではなく、読者がすぐ実践できるノウハウ・テクニック・失敗から学んだ教訓を中心に書いてください。
自己紹介や名乗る場面では必ず「たっくる」という名前を使ってください。

テーマ: {keyword}
{internal_links_section}
## 記事の要件
- 口調: 友達に話しかけるようなカジュアルな一人称（「僕」）
- 文字数: {self.min_chars}文字以上
- 構成: 導入（「これ知らずにキャンプしてたの、もったいなかった」系の共感フック）→ 本題のノウハウ・豆知識（3〜5項目）→ マニアック深掘りコーナー → まとめ（「ぜひ試してみて」）
- 特定のキャンプ場・釣り場・スポット名は登場させない
- 読者が「なるほど！」「知らなかった！」「これ試してみよう」と思える実用情報を中心に
- SEOを意識しつつ、キーワードを自然に含める

## マニアック展開の要件（重要）
- 一般人が知らないようなディープな知識・こだわりポイントを必ず1セクション設ける（見出し例:「たっくる的マニアック視点」「これ知ってる人、相当好きですよね」）
- 道具・技術について「なぜそれが正解か」「プロや上級者はどう考えるか」まで踏み込む
- 数値・スペック・固有名詞を具体的に書く（「含水率〇〇%以下の薪が理想」「ペグは〇〇mm径のスチール製が抜けにくい」など）
- 「実はこれ、知ってる人は知ってるんですが〜」「沼にハマった人はわかると思うんですけど」など、同好の士に語りかけるフレーズを入れる

## 人間らしさ・ユーモアの要件
- 自分の失敗談や「やらかし」エピソードを1〜2個必ず入れる（「知らずにやって大失敗しました（笑）」「完全に舐めてたら返り討ちにあいました」）
- 「正直に言うと〜」「こっそり教えると〜」など、読者だけに話しかけるような表現を使う
- ひとことツッコミや（笑）を適度に使い、読んでいて楽しい文章にする
- まとめは「次のキャンプで試してみてください」「これ知ってるだけで一段上のキャンパーになれます」など、読者の次の行動を後押しする締め

## 出力フォーマット（マーカーは必ず含めること）

===TITLE===
（【番外編】から始めること。例:「【番外編】焚き火の薪、種類で燃え方が全然違う話」。40文字以内）
===END_TITLE===

===EXCERPT===
（120〜160文字の記事概要。「〜を知ってから変わりました」「意外と知られていない〜」調で書く。キーワードを含める）
===END_EXCERPT===

===TAGS===
（記事に関連するタグを5〜8個、カンマ区切りで。例: キャンプ,焚き火,アウトドア,豆知識,初心者）
===END_TAGS===

===CONTENT===
（HTML形式の本文。以下のルールを守ること:
  - 見出しは <h2>、<h3> タグを使用
  - 箇条書きは <ul><li> タグ
  - 重要な語句は <strong> タグで強調
  - 内部リンクは指示がある場合、<a href="URL">アンカーテキスト</a> 形式で自然に挿入
  - 特定のキャンプ場・釣り場・スポット名は書かない
  - 各セクションは読みやすく、空行を適切に入れる）
===END_CONTENT===
"""

    def _parse_response(self, text: str, keyword: str, category: str, is_hobby: bool = False) -> dict:
        def extract(marker: str) -> str:
            start = text.find(f"==={marker}===")
            end = text.find(f"===END_{marker}===")
            if start == -1 or end == -1:
                return ""
            return text[start + len(f"==={marker}==="):end].strip()

        title = extract("TITLE")
        if not title:
            title = f"【番外編】{keyword}に行ってきました！" if is_hobby else f"{keyword}の完全ガイド【テンプレ付き】"

        # 番外編カテゴリなのに【番外編】が付いていない場合は強制付与
        if is_hobby and not title.startswith("【番外編】"):
            title = f"【番外編】{title}"

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
