# teqsnap.com — 自動販売ブログ サイト仕様書

## サイトコンセプト

「AIに乗り遅れないための教科書ブログ」  
ペルソナ: **脳筋タックル**（関西弁・行動力系）  
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
Stripe Payment Links（竹300円 / 松3,000円）
    ↓
サンクスページ（購入者限定コンテンツ）
```

---

## 商品構成（松・竹 二段構え）

| プラン | 価格 | 内容 | Stripe ENV |
|---|---|---|---|
| **竹（標準）** | 300円 | 記事別プロンプト集3選（.txt） | `STRIPE_PAYMENT_URL_TAKE` |
| **松（高級）** | 3,000円 | 全記事プロンプト集＋個別チャット相談1回 | `STRIPE_PAYMENT_URL_MATSU` |

### 購入フロー（竹）
1. 記事末尾CTAバナー「【竹】今すぐ購入（300円）」クリック
2. Stripe決済
3. 決済完了 → サンクスページへリダイレクト
4. サンクスページでパスワード取得
5. WP販売ページ（パスワード保護）でプロンプト集をダウンロード

### 購入フロー（松）※将来展開
1. 記事末尾CTAバナー「【松】フルサポートセット（3,000円）」クリック
2. Stripe決済
3. 決済完了 → サンクスページ（松専用コンテンツ）へリダイレクト
4. 個別チャット相談の日程調整

---

## 記事生成

| 項目 | 設定値 |
|---|---|
| 記事生成モデル | gemini-2.5-flash-lite（→ gemini-2.5-flash → gemini-2.5-pro にフォールバック） |
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

## マスコットキャラクター

サイトの象徴として **脳筋可愛いゴリラ** を起用。親しみやすさと信頼感を両立させる。

| 項目 | 設定値 |
|---|---|
| キャラクター | 筋肉隆々だが瞳クリクリの愛くるしいテックゴリラ |
| スタイル | Pixar/Disney 風 3D クレイアニメ |
| ファイル | `assets/gorilla-mascot.png` |
| 用途 | 全記事のアイキャッチ（OGP）に固定使用 |
| 無効化 | `ENABLE_IMAGES=false` |

---

## ディレクトリ構成

```
auto_blog/
├── main.py                  # メインスクリプト（スケジューラ）
├── article_generator.py     # Gemini で記事生成
├── image_generator.py       # マスコット画像（gorilla-mascot.png）をロード
├── assets/
│   └── gorilla-mascot.png   # 専属マスコット（全記事共通アイキャッチ）
├── wordpress_poster.py      # WP REST API 投稿
├── product_generator.py     # プロンプト集生成
├── product_seller.py        # WP販売ページ作成・CTA生成（松竹対応）
├── stripe_setup.py          # Stripe Payment Link 生成（松竹両対応）
├── create_thanks_page.py    # サンクスページ作成・更新
├── repost_last3.py          # 直近N記事の再生成・更新
├── repost_ids.py            # wp_id指定で再生成・更新
├── keyword_manager.py       # キーワード管理
├── internal_link_manager.py # 内部リンク管理
├── keywords.txt             # キーワード一覧
├── published_articles.json  # 投稿済み記事DB
├── .env                     # 環境変数（Git管理外）
└── products/                # 生成されたプロンプト集
```

---

## 環境変数（.env）

```
GEMINI_API_KEY=
WP_URL=https://teqsnap.com
WP_USERNAME=
WP_APP_PASSWORD=
STRIPE_SECRET_KEY=           # Stripe シークレットキー
STRIPE_PAYMENT_URL=          # 竹 Payment Link（後方互換用）
STRIPE_PAYMENT_URL_TAKE=     # 竹（300円）Payment Link
STRIPE_PAYMENT_URL_MATSU=    # 松（3,000円）Payment Link
THANKS_PAGE_URL=https://teqsnap.com/thanks-95bb6f0c3e9c9ad2/
PRODUCT_PRICE=300
PRODUCT_PRICE_MATSU=3000
PRODUCT_PASSWORD=            # WP販売ページのパスワード
ENABLE_PRODUCT=true
ENABLE_IMAGES=true
IMAGE_MAX_PER_ARTICLE=2
POST_TIMES=08:00,13:00,20:00
ARTICLE_MIN_CHARS=1500
```
