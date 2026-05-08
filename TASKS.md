# TASKS.md — 進捗管理

最終更新: 2026-05-08

---

## ✅ 完了済み

### インフラ・認証
- [x] GitHub アカウント (`heytakkuru-bit`) ブラウザ認証
- [x] Google AI Studio 課金有効化（5,000円チャージ）
- [x] WordPress REST API 接続確認（teqsnap.com）

### 記事生成システム
- [x] Gemini API による記事自動生成（キーワード → 記事）
- [x] 内部リンク自動挿入
- [x] 1日3回スケジュール自動投稿（08:00 / 13:00 / 20:00）
- [x] カテゴリ自動作成・タグ自動付与
- [x] 番外編（趣味ログ）を6記事に1回混在

### ビジュアル強化
- [x] `gemini-2.5-flash-image` による AI 画像生成
- [x] WP メディアライブラリへの画像アップロード
- [x] アイキャッチ自動設定
- [x] カラーコールアウトBOX（4種）
- [x] ステップカード・比較テーブル・まとめBOX（inline style）

### ペルソナ・文体
- [x] ペルソナ名: 「脳筋でタックルしかできないタックル」
- [x] 文体: 関西弁に統一
- [x] ターゲット: AIに乗り遅れた初心者向け「教科書」スタイル
- [x] 番外編も同ペルソナ・関西弁適用

### デジタル商材・Stripe
- [x] プロンプト集自動生成（keyword → .txt ファイル）
- [x] WP パスワード保護販売ページ自動作成
- [x] CTA バナー（記事末尾）自動挿入
- [x] Stripe Payment Links 生成スクリプト作成（`stripe_setup.py`）
- [x] サンクスページ URL 設定（`THANKS_PAGE_URL`）

### ドキュメント
- [x] SPEC.md 作成
- [x] CLAUDE.md 作成
- [x] TASKS.md 作成（このファイル）

---

## 🔲 残タスク

### 優先度: 高
- [ ] **Stripe シークレットキーを `.env` に追加**  
  → `STRIPE_SECRET_KEY=sk_live_...` を追記
- [ ] **`python3 stripe_setup.py` を実行して Payment Link を発行**  
  → 成功すると `.env` の `STRIPE_PAYMENT_URL` が自動更新
- [ ] **`python3 repost_last3.py 3` を実行して全記事に決済ボタンを反映**

### 優先度: 中
- [ ] GitHub Actions の自動投稿ワークフロー確認・更新  
  （`.github/workflows/daily_post.yml` — Node.js 24 対応済みか確認）
- [ ] キーワード追加（現在残り 98/115 件）
- [ ] サンクスページのデザイン確認・改善

### 優先度: 低
- [ ] Python 3.11+ へのアップグレード検討
- [ ] `requirements.txt` に `stripe` を追加
- [ ] 投稿済み記事のSEOスコア確認

---

## 📊 現在の数字

| 指標 | 値 |
|---|---|
| 総キーワード数 | 115 |
| 投稿済み | 17 |
| 残り | 98 |
| WordPress 投稿 ID 最大値 | 54 |
| 使用画像モデル | gemini-2.5-flash-image |
| 使用記事モデル | gemini-2.5-flash-lite |
