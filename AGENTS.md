# AGENTS.md — aituber

このリポジトリのエージェント向け運用情報は **AGENTS.md を正本** とする。
`CLAUDE.md` は AGENTS.md への参照ファイルとして扱う。

---

## プロジェクト概要

録画ゲーム動画を入力として AI が実況テキスト・音声・字幕を生成し、実況付き動画を出力するシステム。
FastAPI + PostgreSQL + Qwen TTS + LLM API で構成する Python バックエンド。

---

## セットアップ

```bash
# 仮想環境作成
python3 -m venv .venv

# 依存関係インストール
.venv/bin/python -m pip install -e ".[dev]"

# pre-commit フック設定
.venv/bin/pre-commit install

# 環境変数設定
cp .env.example .env
# .env を編集して DATABASE_URL, LLM_API_KEY 等を設定

# DB 起動（Docker）
docker compose -f docker/docker-compose.yml up -d db redis

# マイグレーション
.venv/bin/alembic upgrade head

# サーバー起動
.venv/bin/uvicorn app.main:app --reload
```

---

## 主要コマンド

```bash
# テスト実行
.venv/bin/pytest tests/ -v

# Lint / フォーマット
.venv/bin/ruff check .
.venv/bin/ruff format .

# pre-commit 全実行
.venv/bin/pre-commit run --all-files

# マイグレーション生成
.venv/bin/alembic revision --autogenerate -m "説明"
.venv/bin/alembic upgrade head

# パイプライン一括実行（開発用）
.venv/bin/python scripts/run_pipeline.py --input sample_data/videos/sample_match.mp4
```

---

## プロジェクト構成

```text
aituber/
├── app/
│   ├── main.py              # FastAPI エントリーポイント（ルーター登録のみ）
│   ├── api/                 # REST API ルーター（HTTPのみ、ビジネスロジックなし）
│   ├── core/                # ドメインロジック（外部依存禁止: httpx・sqlalchemy 不可）
│   ├── models/              # SQLAlchemy モデル + Pydantic スキーマ
│   ├── clients/             # 外部 API クライアント（LLM / TTS）
│   ├── db/                  # DB セッション・Alembic 設定
│   ├── config/              # pydantic-settings による設定読み込み
│   └── utils/               # ログ・ファイル操作ユーティリティ
├── scripts/
├── tests/
├── docker/
├── docs/
└── sample_data/
```

---

## アーキテクチャ概要

```text
mp4 入力
  -> SegmentationService
  -> VisionService
  -> EventService
  -> UtterancePlanner
  -> CommentaryService
  -> QwenTTSClient + SubtitleService
  -> Composer
  -> mp4 出力
```

---

## 参照ドキュメント

- `docs/01_requirements/requirements.md`（要件定義）
- `docs/02_design/system_design.md`（設計）
- `docs/03_standards/python_coding_standard.md`（コーディング規約）
- `docs/03_standards/test_review_standard.md`（テスト・レビュー規約）
- `docs/04_api/api_reference.md`（API）
- `docs/05_git/git_strategy.md`（Git 戦略）

---

## コーディング規則

- 型ヒントを全関数に付ける
- コメント・docstring は日本語
- `app/core/` は `httpx` / `sqlalchemy` を import しない
- エラーは `logger.error(...)` に記録してから再 raise
- `ruff check` エラーゼロを維持する

---

## Git ルール

- `main` への直接 push 禁止（PR 経由のみ）
- ブランチ: `feature/` `fix/` `docs/` `refactor/` `chore/`
- コミット: `feat:` `fix:` `docs:` `refactor:` `chore:` `test:`

---

## Issue 管理

- 作業開始時は `start` スキルで Issue 確認から開始する
- PR には `Closes #XX` を含めて Issue と紐付ける
- 新規課題・不具合は `create-issue` スキルで登録する

---

## テスト方針

- CI（GitHub Actions）は使用しない。テストはローカル実行
- 外部依存（DB・外部 API）は `pytest-mock` でモック化
- 正常系・異常系の両方を必ずカバーする
- テスト名: `test_<対象>_<条件>_<期待結果>`
- PR 前に `.venv/bin/pre-commit run --all-files` と `.venv/bin/pytest` を実行する

---

## 重要な注意事項

- `.env` はコミットしない（`.gitignore` 済み）
- `sample_data/videos/` の mp4 はコミットしない
- DB マイグレーションは自動生成後に内容確認してからコミットする
- `app/core/` に外部 API 呼び出しを追加しない（`app/clients/` に実装する）
- Discord 通知は Git hooks ではなく Codex hooks（`.codex/hooks/`）を使う

---

## Skills

共通スキル:
- `start` / `ship` / `sync-main` / `new-feature` / `long-run`
- `create-issue` / `update-skill`
- `review` / `py-review` / `test-check`

スキル実体:
- Codex: `.codex/skills/<skill-name>/SKILL.md`
- Claude: `.claude/skills/<skill-name>/SKILL.md`
