# CLAUDE.md — Claude Code 開発ルール

## 環境

- **OS**: macOS (Darwin 24.x)
- **Python**: 3.9（`python3` コマンド）
- **Node.js**: v24.x
- **パッケージ管理**: pip3
- **作業ディレクトリ**: `/Users/koki.nakamura/auto_blog`

---

## ビルド・実行手順

### セットアップ

```bash
cd /Users/koki.nakamura/auto_blog
pip3 install -r requirements.txt
pip3 install stripe   # Stripe SDK（requirements未収録）
```

### 動作確認

```bash
python3 main.py verify          # WordPress 接続確認
python3 main.py status          # キーワード残数・投稿済み確認
```

### 記事投稿

```bash
python3 main.py post-one        # 1記事だけ投稿
python3 main.py run-now         # 3記事まとめて投稿
python3 main.py                 # スケジューラ起動（08:00/13:00/20:00）
```

### 記事再生成・更新

```bash
python3 repost_last3.py 1       # 直近1記事を再生成して更新
python3 repost_last3.py 3       # 直近3記事を再生成して更新
```

### Stripe 決済リンク生成

```bash
# .env に STRIPE_SECRET_KEY=sk_live_... を追記してから実行
python3 stripe_setup.py
# → .env の STRIPE_PAYMENT_URL が自動更新される
```

### デプロイ（GitHub プッシュ）

```bash
git add -p                      # 変更を確認しながらステージング
git commit -m "feat: ..."
git push origin main
```

---

## 画像生成ルール

- **使用モデル**: `gemini-2.5-flash-image`（固定）
- **スタイル**: リアル写真スタイル（`generate_content` + `response_modalities=["IMAGE"]`）
- **生成枚数**: 記事あたり最大2枚（`IMAGE_MAX_PER_ARTICLE` 環境変数で変更可）
- **課金**: Google AI Studio の課金有効時のみ動作
- 画像生成に失敗しても記事投稿は止めない（例外を握り潰す設計）

## 記事生成ルール

- **メインモデル**: `gemini-2.5-flash-lite`
- **フォールバック順**: `gemini-2.5-flash` → `gemini-2.0-flash-lite` → `gemini-2.0-flash`
- 404 / 429 / 503 エラーは次のモデルにフォールバック
- ペルソナ名: **脳筋タックル**
- 文体: **関西弁**

## コーディング規約

- Python 3.9 互換（`X | Y` 型ヒント禁止 → `Optional[X]` を使う）
- ログは `logging` モジュールで統一
- 外部API呼び出しは必ず try/except でラップし、失敗しても処理継続
- 環境変数は `.env` から `python-dotenv` で読み込む
- `.env` は Git 管理外（`.gitignore` 済み）

## 禁止事項

- `gemini-2.0-flash` をデフォルトモデルに使わない（有料プランで廃止）
- `bytes | None` など 3.10+ 構文を使わない
- `.env` を Git にコミットしない
