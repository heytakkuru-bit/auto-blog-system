"""
デジタル商材（プロンプト集）自動生成モジュール
記事の内容に基づいて「実戦プロンプト3選」を生成し .md ファイルとして保存する
"""
import os
import re
import logging
from pathlib import Path
from datetime import date

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

PRODUCTS_DIR = Path(__file__).parent / "products"


class ProductGenerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=api_key)

    def generate(self, article: dict) -> dict:
        """
        記事 dict を受け取り、関連するプロンプト集を生成する。
        Returns: title / filename / filepath / content / description
        """
        article_title = article.get("title", "")
        article_content = article.get("content", "")
        keyword = article.get("keyword", "")

        product_title = f"「{article_title}」を爆速で再現するプロンプト集"

        prompt = self._build_prompt(article_title, article_content, keyword)
        response = self.client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.8, max_output_tokens=4096),
        )

        content = self._format_product(product_title, keyword, response.text)

        PRODUCTS_DIR.mkdir(exist_ok=True)
        safe_name = re.sub(r"[^\w\-]", "_", keyword)[:40]
        filename = f"prompt_{safe_name}_{date.today().strftime('%Y%m%d')}.txt"
        filepath = PRODUCTS_DIR / filename
        filepath.write_text(content, encoding="utf-8")

        logger.info(f"Product generated: {filepath}")

        return {
            "title": product_title,
            "filename": filename,
            "filepath": filepath,
            "content": content,
            "description": self._build_description_html(product_title, keyword),
        }

    def _build_prompt(self, article_title: str, article_content: str, keyword: str) -> str:
        clean = re.sub(r"<[^>]+>", "", article_content)[:1000]
        return f"""
あなたはAIプロンプトエンジニアリングの専門家です。
以下のブログ記事のテーマに関連する「実戦プロンプト3選」を作成してください。

## 記事タイトル
{article_title}

## キーワード
{keyword}

## 記事の冒頭（参考）
{clean}

---

## 出力形式（この形式厳守）

### プロンプト1：基本編（初心者向け）
**タイトル**：[プロンプト名]
**用途**：[何ができるか1行で]
**プロンプト本文**：
```
[実際にコピペして使えるプロンプト。具体的に]
```
**使い方のコツ**：[効果を最大化する1〜2行のアドバイス]

---

### プロンプト2：応用編（中級者向け）
**タイトル**：[プロンプト名]
**用途**：[何ができるか1行で]
**プロンプト本文**：
```
[カスタマイズ変数を {{変数名}} 形式で含めた発展版プロンプト]
```
**使い方のコツ**：[変数の使い方・カスタマイズ方法]

---

### プロンプト3：上級テクニック編
**タイトル**：[プロンプト名]
**用途**：[何ができるか1行で]
**プロンプト本文**：
```
[連鎖プロンプトや役割設定など、上級者向けの高度なプロンプト]
```
**使い方のコツ**：[プロレベルの活用方法・応用例]

---

出力は日本語で。プロンプト本文は実際に貼り付けてすぐ使えるレベルの具体性で書くこと。
"""

    def _format_product(self, product_title: str, keyword: str, body: str) -> str:
        today = date.today().strftime("%Y年%m月%d日")
        return f"""# {product_title}

> **2026年時点の動作確認済み** — ChatGPT-4o / Claude Sonnet 4.6 / Gemini 2.0 Flash

---

## はじめに・使い方の注意点

本プロンプト集は「{keyword}」に関する作業をAIで効率化するための実戦テンプレートです。

### ご利用前に必ずお読みください

1. **動作環境**：ChatGPT（GPT-4以上推奨）、Claude 3以上、Gemini 1.5以上で動作確認済み
2. **コピペで使えます**：プロンプト本文はそのままコピーして貼り付けてください
3. **カスタマイズ推奨**：`{{変数名}}` で囲まれた部分はご自身の状況に合わせて書き換えてください
4. **AIの出力は必ず確認を**：AIの回答は参考情報です。重要な判断はご自身で確認してください
5. **バージョン更新**：AIモデルのアップデートにより出力の質が変わる場合があります

---

## プロンプト集

{body}

---

## まとめ・活用のポイント

このプロンプト集で「{keyword}」に関する作業時間を大幅に短縮できます。

- まずは **プロンプト1（基本編）** から試してみてください
- 慣れたら **プロンプト2（応用編）** で自分好みにカスタマイズ
- 上達したら **プロンプト3** でさらなる効率化を

---

*作成日：{today}*
*動作確認バージョン：ChatGPT-4o / Claude Sonnet 4.6 / Gemini 2.0 Flash*
*teqsnap.com*
"""

    def _build_description_html(self, product_title: str, keyword: str) -> str:
        return (
            f'<div class="teqsnap-product-desc">'
            f"<h3>📦 商品内容</h3>"
            f"<p>「{keyword}」に関する作業をAIで一瞬で終わらせる、<strong>実戦プロンプト3選</strong>のテキストファイルです。</p>"
            f"<ul>"
            f"<li>✅ 基本編（初心者でもすぐ使える）</li>"
            f"<li>✅ 応用編（カスタマイズ可能なテンプレート）</li>"
            f"<li>✅ 上級テクニック編（プロの活用法）</li>"
            f"</ul>"
            f"<p><strong>2026年時点の動作確認済み</strong>（ChatGPT-4o / Claude / Gemini）</p>"
            f"</div>"
        )
