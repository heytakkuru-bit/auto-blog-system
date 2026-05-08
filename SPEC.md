# teqsnap.com — 自動販売ブログ サイト仕様書

## サイトコンセプト

「AIに乗り遅れないための教科書ブログ」  
ペルソナ: **脳筋でタックルしかできないタックル**（関西弁・行動力系）  
ターゲット: AIに乗り遅れていると感じている初心者〜中級者

---

## システム構成

```
Gemini API（記事生成・画像生成）
    ↓
auto_blog/ （Python スクリプト群）
    ↓
WordPress REST API（teqsnap.com）
    ↓
Stripe Payment Links（300円商品）
```

---

## 記事生成

| 項目 | 設定値 |
|---|---|
| 記事生成モデル | gemini-2.5-flash-lite（→ gemini-2.5-flash にフォールバック） |
| 最低文字数 | 1,500文字 |
| 投稿スケジュール | 08:00 / 13:00 / 20:00（1日3回） |
| カテゴリ | 生成AI・プロンプト系 / WordPress・ブログ系 / 番外編・趣味ログ |
| 番外編の割合 | 6記事に1回 |

### ビジュアル要素（全記事必須）

- カラーコールアウトBOX（ポイント/詰む/感動/期待外れ）
- ステップカード（手順説明）
- 比較テーブル（他ツール比較）
- グラデーションまとめBOX
- AI生成画像（2枚/記事）→ アイキャッチ + 本文挿入

---

## 画像生成

| 項目 | 設定値 |
|---|---|
| 使用モデル | `gemini-2.5-flash-image` |
| 生成枚数 | 最大2枚/記事（`IMAGE_MAX_PER_ARTICLE` で制御） |
| スタイル | リアル写真スタイル（フラットイラストではない） |
| 無効化 | `ENABLE_IMAGES=false` で画像生成をスキップ |
| 使用SDK | google-genai >= 1.0.0 |

---

## デジタル商材・Stripe決済

| 項目 | 設定値 |
|---|---|
| 商品 | 実戦プロンプト集3選（.txt） |
| 価格 | 300円（固定） |
| 決済 | Stripe Payment Links |
| 決済後 | サンクスページ（`THANKS_PAGE_URL`）へリダイレクト |
| サンクスページ | https://teqsnap.com/thanks-95bb6f0c3e9c9ad2/ |
| CTA設置 | 通常記事末尾に自動挿入（番外編は除外） |

### 購入フロー

1. 記事末尾のCTAバナーをクリック
2. Stripe決済ページ（300円）
3. 決済完了 → サンクスページへリダイレクト
4. サンクスページでパスワードを取得
5. WP販売ページ（パスワード保護）でプロンプト集をダウンロード

---

## ディレクトリ構成

```
auto_blog/
├── main.py                 # メインスクリプト（スケジューラ）
├── article_generator.py    # Gemini で記事生成
├── image_generator.py      # Gemini で画像生成
├── wordpress_poster.py     # WP REST API 投稿
├── product_generator.py    # プロンプト集生成
├── product_seller.py       # WP販売ページ作成・CTA生成
├── stripe_setup.py         # Stripe Payment Link 生成
├── repost_last3.py         # 直近N記事の再生成・更新
├── keyword_manager.py      # キーワード管理
├── internal_link_manager.py # 内部リンク管理
├── keywords.txt            # キーワード一覧
├── published_articles.json # 投稿済み記事DB
├── .env                    # 環境変数（Git管理外）
└── products/               # 生成されたプロンプト集
```

---

## 環境変数（.env）

```
GEMINI_API_KEY=           # Google AI Studio APIキー
WP_URL=                   # WordPress URL
WP_USERNAME=              # WPログインメール
WP_APP_PASSWORD=          # WPアプリケーションパスワード
STRIPE_SECRET_KEY=        # Stripe シークレットキー
STRIPE_PAYMENT_URL=       # 生成したPayment Link URL
THANKS_PAGE_URL=          # 決済後リダイレクトURL
PRODUCT_PRICE=300
PRODUCT_PASSWORD=         # WP販売ページのパスワード
ENABLE_PRODUCT=true
ENABLE_IMAGES=true
IMAGE_MAX_PER_ARTICLE=2
POST_TIMES=08:00,13:00,20:00
ARTICLE_MIN_CHARS=1500
```
