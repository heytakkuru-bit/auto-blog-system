# TASKS.md — 進捗管理

最終更新: 2026-05-09

---

## ✅ 完了済み

### インフラ・認証
- [x] GitHub アカウント (`heytakkuru-bit`) ブラウザ認証
- [x] Google AI Studio 課金有効化（5,000円チャージ）
- [x] WordPress REST API 接続確認（teqsnap.com）

### 記事生成システム
- [x] Gemini API による記事自動生成（1日3回: 08:00/13:00/20:00）
- [x] 内部リンク自動挿入
- [x] 番外編（趣味ログ）を6記事に1回混在
- [x] カテゴリ・タグ自動作成

### ビジュアル強化
- [x] `gemini-2.5-flash-image` による AI 画像生成（リアル写真スタイル）
- [x] アイキャッチ自動設定
- [x] カラーコールアウトBOX 4種
- [x] ステップカード・比較テーブル・まとめBOX（inline style）

### ペルソナ・文体
- [x] ペルソナ名: 「脳筋タックル」
- [x] 文体: 関西弁
- [x] ターゲット: AIに乗り遅れた初心者向け「教科書」スタイル

### デジタル商材・Stripe（竹）
- [x] プロンプト集自動生成（keyword → .txt ファイル）
- [x] WP パスワード保護販売ページ自動作成
- [x] CTA バナー（竹メイン＋松プレースホルダー）
- [x] stripe_setup.py: 竹・松両方の Payment Link 生成スクリプト
- [x] サンクスページ作成・更新（パスワード表示済み）

### ブランドイメージ
- [x] 脳筋可愛いゴリラ マスコット生成（assets/gorilla-mascot.png）
- [x] 全記事アイキャッチをゴリラ固定に変更（image_generator.py 書き換え）

### ドキュメント
- [x] SPEC.md（松竹二段構え販売モデル対応）
- [x] CLAUDE.md
- [x] TASKS.md（このファイル）

---

## 🔲 残タスク

### 優先度: 高（Stripe 決済の安定化）
- [ ] **`.env` に `STRIPE_SECRET_KEY=sk_live_...` を追記**
- [ ] **`python3 stripe_setup.py take` で竹（300円）Payment Link を発行**
- [ ] **`python3 repost_last3.py 3` で直近3記事に決済ボタンを反映**
- [ ] Stripe Webhook 設定・決済完了フローの動作確認

### 優先度: 中（松の準備）
- [ ] 松（3,000円）の商品内容を確定
  - 全記事プロンプト集セット
  - 個別チャット相談の提供方法（Calendly / Discord など）
- [ ] `python3 stripe_setup.py matsu` で松 Payment Link を発行
- [ ] サンクスページに松専用コンテンツを追加
- [ ] GitHub Actions の自動投稿ワークフロー確認

### 優先度: 低
- [ ] キーワード追加（現在残り 98/115 件）
- [ ] Python 3.11+ へのアップグレード検討
- [ ] 投稿済み記事の SEO スコア確認

---

## 📊 現在の数字

| 指標 | 値 |
|---|---|
| 総キーワード数 | 115 |
| 投稿済み | 17 |
| 残り | 98 |
| 使用画像モデル | gemini-2.5-flash-image |
| 使用記事モデル | gemini-2.5-flash-lite |
| 竹価格 | 300円 |
| 松価格 | 3,000円（準備中） |
| サンクスページ | https://teqsnap.com/thanks-95bb6f0c3e9c9ad2/ |
