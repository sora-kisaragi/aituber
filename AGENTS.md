# AGENTS.md — aituber

録画ゲーム動画を入力として AI が実況テキスト・音声・字幕を生成し、実況付き動画を出力するシステム。
FastAPI + PostgreSQL + Qwen TTS + LLM API で構成する Python バックエンド。

---

## セットアップ

```bash
# 依存関係インストール
pip install -e ".[dev]"

# pre-commit フック設定
pre-commit install

# 環境変数設定
cp .env.example .env
# .env を編集して DATABASE_URL, LLM_API_KEY 等を設定

# DB 起動（Docker）
docker compose -f docker/docker-compose.yml up -d db redis

# マイグレーション
alembic upgrade head

# サーバー起動
uvicorn app.main:app --reload
```

---

## 主要コマンド

```bash
# テスト実行
pytest tests/ -v

# Lint / フォーマット
ruff check .
ruff format .

# pre-commit 全実行
pre-commit run --all-files

# マイグレーション生成
alembic revision --autogenerate -m "説明"
alembic upgrade head

# パイプライン一括実行（開発用）
python scripts/run_pipeline.py --input sample_data/videos/sample_match.mp4
```

---

## プロジェクト構成

```
app/
├── main.py              # FastAPI エントリーポイント（ルーター登録のみ）
├── api/                 # REST API ルーター（HTTPのみ、ビジネスロジックなし）
├── core/                # ドメインロジック（外部依存禁止：httpx・sqlalchemy 不可）
├── models/              # SQLAlchemy モデル + Pydantic スキーマ
├── clients/             # 外部 API クライアント（LLM / TTS）
├── db/                  # DB セッション・Alembic 設定
├── config/              # pydantic-settings による設定読み込み
└── utils/               # ログ・ファイル操作ユーティリティ
```

---

## コーディング規則

- 型ヒントを全関数に付ける
- `app/core/` は `httpx` / `sqlalchemy` を import しない
- エラーは `logger.error(...)` に記録してから再 raise
- コメント・docstring は日本語
- `ruff check` エラーゼロを維持する
- 詳細: `docs/03_standards/python_coding_standard.md`

---

## Git ルール

- `main` への直接 push 禁止（PR 経由のみ）
- ブランチ: `feature/` `fix/` `docs/` `refactor/` `chore/`
- コミット: `feat:` `fix:` `docs:` `refactor:` `chore:` `test:`
- 詳細: `docs/05_git/git_strategy.md`

---

## テスト方針

- 外部依存（DB・外部 API）は `pytest-mock` でモック化
- 正常系・異常系の両方を必ずカバーする
- テスト名: `test_<対象>_<条件>_<期待結果>`
- 詳細: `docs/03_standards/test_review_standard.md`

---

## 重要な注意事項

- `.env` ファイルは絶対にコミットしない（`.gitignore` 済み）
- `sample_data/videos/` の mp4 ファイルはコミットしない
- DB マイグレーションは `alembic revision --autogenerate` で自動生成後、内容を必ず確認してからコミットする
- `app/core/` に外部 API 呼び出しを追加しない。`app/clients/` に実装する

---

## Skills

Codex でよく使う操作はスキルとして定義されています。

| スキル | 用途 |
|---|---|
| `new-feature` | feature ブランチを切って開発開始 |
| `ship` | コミット → push → PR 作成の一連操作 |
| `sync-main` | main を最新に同期してリベース |
| `review` | テスト・レビュー規約に基づくレビュー |
| `py-review` | Python コーディング規約に基づくレビュー |
| `test-check` | 実装完了判定チェックリスト |
| `start` | 作業開始時の Issue 確認・ブランチ作成 |
| `create-issue` | GitHub Issue 登録 |
| `update-skill` | 使用したスキルの振り返りと SKILL.md 更新 |
