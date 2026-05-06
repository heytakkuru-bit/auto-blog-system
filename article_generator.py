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
あなたはSEOに精通しつつ、読者に親しみやすく語りかけるブログライターです。
「情報をただ並べるだけ」ではなく、読んでいて「なるほど！」「わかる〜」と思えるような、人間味のある文章を{self.language}で書いてください。

キーワード: {keyword}
{category_hint}{internal_links_section}
## 記事の要件
- 読者ターゲット: 初心者〜中級者
- 文字数: {self.min_chars}文字以上
- 構成: 導入（共感できる課題提起）→ 本文（具体的な手順・解説）→ まとめ（背中を押す一言）
- SEOを意識し、キーワードを自然に本文に含める
- 具体的な手順や例文、テンプレートがあれば積極的に含める

## 文体・トーンの要件（重要）
- 導入は「〜で困ったことありませんか？」「実は私も最初はそう思っていました」など、読者の気持ちに寄り添う一言から始める
- 堅苦しくなりすぎず、ところどころに軽いユーモアや「あるある」ネタを自然に挿入する（例:「最初は正直よくわからなかったんですが…（笑）」）
- 読者に話しかけるような温かい口調を意識する（「〜してみてください」「ぜひ試してみてほしいのですが」など）
- 「ちなみに」「実は」「意外と」などのクッション言葉を使って、自然な会話の流れを作る
- まとめでは「一緒に頑張りましょう」「少しでも参考になれば嬉しいです」など、読者への温かいメッセージで締める

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
釣りやキャンプ、ジムニーでの車旅など、実際の体験をもとにした、笑えて温かみのあるブログ記事を書いてください。
自己紹介や名乗る場面では必ず「たっくる」という名前を使ってください。

テーマ: {keyword}
{internal_links_section}
## 記事の要件
- 口調: 友達に話しかけるようなカジュアルな一人称（「僕」）
- 文字数: {self.min_chars}文字以上
- 構成: 体験談の導入（「〜してきました！」）→ 現地・体験の詳細レポート → マニアック深掘りコーナー → 感想・おすすめポイント → まとめ
- 「〜だった！」「〜してみて最高でした」など体験談らしい表現を使う
- 読者が「自分も行ってみたい／やってみたい」と思えるような臨場感を出す
- SEOを意識しつつ、キーワードを自然に含める

## マニアック展開の要件（重要）
- 一般人が知らないようなディープな知識・こだわりポイントを必ず1セクション設ける（例:「たっくる的マニアック視点」「ここだけの話」などの見出しで）
- 道具・場所・技術について「なぜそれを選んだか」「プロや上級者はどう考えるか」まで踏み込む
- 数値・スペック・固有名詞を具体的に書く（「竿は〇〇の〇〇番」「タイドグラフで〇時前後の下げ三分」など）
- 「実はこれ、知ってる人は知ってるんですが〜」「沼にハマった人はわかると思うんですけど」など、同好の士に語りかけるフレーズを入れる

## 人間らしさ・ユーモアの要件
- 失敗談や「やらかし」エピソードを1〜2個必ず入れる（例:「道を間違えて30分ロスしました（笑）」「完全に舐めてたら返り討ちにあいました」）
- 天気・気分・同行者とのやりとりなど、リアルな「あの日の空気感」が伝わる描写を入れる
- 「正直に言うと〜」「こっそり教えると〜」など、読者だけに話しかけるような表現を使う
- ひとことツッコミや（笑）を適度に使い、読んでいて楽しい文章にする
- まとめは「また行きたい」「次は〇〇に挑戦したい」など、次の冒険への期待感で締める

## 出力フォーマット（マーカーは必ず含めること）

===TITLE===
（【番外編】から始めること。例:「【番外編】神奈川で釣りしてきた！初心者でも釣れたスポット3選」。40文字以内）
===END_TITLE===

===EXCERPT===
（120〜160文字の記事概要。体験談らしく「〜してきました」調で書く。キーワードを含める）
===END_EXCERPT===

===TAGS===
（記事に関連するタグを5〜8個、カンマ区切りで。例: 釣り,神奈川,アウトドア,体験レポート,初心者）
===END_TAGS===

===CONTENT===
（HTML形式の本文。以下のルールを守ること:
  - 見出しは <h2>、<h3> タグを使用
  - 箇条書きは <ul><li> タグ
  - 重要な語句は <strong> タグで強調
  - 内部リンクは指示がある場合、<a href="URL">アンカーテキスト</a> 形式で自然に挿入
  - 体験談・感想・失敗談なども交える
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
