# CLAUDE.md — aituber

録画ゲーム動画を入力として AI が実況テキスト・音声・字幕を生成し、実況付き動画を出力するシステム。
FastAPI + PostgreSQL + Qwen TTS + LLM API で構成する Python バックエンド。

---

## プロジェクト構成

```
aituber/
├── app/
│   ├── main.py              # FastAPI エントリーポイント
│   ├── api/                 # REST API ルーター
│   ├── core/                # ドメインロジック（純粋 Python、外部依存なし）
│   ├── models/              # SQLAlchemy モデル + Pydantic スキーマ
│   ├── clients/             # 外部 API クライアント（LLM / TTS）
│   ├── db/                  # DB セッション・マイグレーション設定
│   ├── config/              # 設定読み込み（pydantic-settings）
│   └── utils/               # ロギング・ファイル操作ユーティリティ
├── scripts/                 # パイプライン実行・データ準備スクリプト
├── tests/                   # pytest テスト（test_api / test_core / test_clients）
├── docker/                  # Dockerfile・docker-compose.yml
├── docs/                    # 設計・規約・API ドキュメント
└── sample_data/             # 開発・テスト用サンプル動画・アノテーション
```

---

## ドキュメント一覧

| ドキュメント | 内容 |
|---|---|
| [要件定義](docs/01_requirements/requirements.md) | 機能要件・MVP スコープ |
| [設計書](docs/02_design/system_design.md) | アーキテクチャ・クラス設計・データモデル |
| [コーディング規約](docs/03_standards/python_coding_standard.md) | Python / FastAPI 規約 |
| [テスト・レビュー規約](docs/03_standards/test_review_standard.md) | 実装完了定義・レビュー観点 |
| [API リファレンス](docs/04_api/api_reference.md) | REST API エンドポイント仕様 |
| [Git 戦略](docs/05_git/git_strategy.md) | ブランチ・コミット・PR ルール |
| [テスト記録](docs/06_test/README.md) | 動作確認結果の記録 |

---

## アーキテクチャ概要

```
mp4 入力
   ↓
SegmentationService（FFmpeg で分割）
   ↓
VisionService（フレーム抽出・VLM 解析）
   ↓
EventService（ゲームイベント検出）
   ↓
UtterancePlanner（発話計画・優先度付け）
   ↓
CommentaryService（LLM で実況文生成）
   ↓
QwenTTSClient（音声合成）+ SubtitleService（SRT 生成）
   ↓
Composer（FFmpeg で音声・字幕・動画合成）
   ↓
mp4 出力
```

- `app/core/` は純粋なビジネスロジック。ファイル I/O・API 呼び出しは `app/clients/` に委譲
- DB は PostgreSQL + JSONB。セグメント単位で並列処理可能な設計
- 音声生成は Qwen TTS API（`TTS_BASE_URL`）、LLM は OpenAI 互換 API

---

## コーディング規則（要約）

- コメントは **日本語**
- 型ヒントを必ず付ける（`mypy --strict` レベルを目標）
- `app/core/` は外部依存（httpx・sqlalchemy）を import しない
- `app/clients/` は外部 API の呼び出しと応答パースのみ行う
- 詳細は [コーディング規約](docs/03_standards/python_coding_standard.md) を参照

---

## Issue 管理

GitHub Issues でタスク・バグを可視化する。

| 種別 | 用途 | Label |
|---|---|---|
| **Epic Issue** | フェーズ単位の大きな目標 | `epic` + `phase:mvp / quality / ops` |
| **Task Issue** | 実装タスク単位（1〜3 日で完了する粒度） | `phase:mvp / quality / ops` |
| **Bug Issue** | 不具合・警告 | `bug` + `priority:S/A/B` |

### 運用ルール

- 作業開始時は `/start` でブランチ作成まで一括実行
- PR は必ず `Closes #XX` で Issue に紐付ける
- 発見した不具合は `/create-issue` で即登録

---

## Git ルール（要約）

- ブランチ: `feature/` `fix/` `docs/` `refactor/` `chore/`
- コミット: `feat:` `fix:` `docs:` `refactor:` `chore:` `test:`
- `main` への直接 push 禁止・PR 経由のみ
- 詳細は [Git 戦略](docs/05_git/git_strategy.md) を参照

---

## 対応環境

| 項目 | 内容 |
|---|---|
| Python | 3.11+ |
| OS | Linux / Windows（Docker 推奨） |
| DB | PostgreSQL 16 |
| TTS | Qwen TTS（ローカルサーバー） — `TTS_BASE_URL` |
| LLM | OpenAI 互換 API — `LLM_API_BASE` |
| 動画処理 | FFmpeg + OpenCV |

---

## Skills

Claude Code でよく使う操作はスキルとして定義されています。

### Git 操作

| スキル | 用途 |
|---|---|
| [new-feature](.claude/skills/new-feature/SKILL.md) | feature ブランチを切って開発開始 |
| [ship](.claude/skills/ship/SKILL.md) | コミット → push → PR 作成の一連操作 |
| [sync-main](.claude/skills/sync-main/SKILL.md) | main を最新に同期してブランチをリベース |

### コーディング規約

| スキル | 用途 |
|---|---|
| [py-review](.claude/skills/py-review/SKILL.md) | Python コーディング規約に基づくレビュー |

### テスト・レビュー

| スキル | 用途 |
|---|---|
| [review](.claude/skills/review/SKILL.md) | 実装後のレビュー観点チェック |
| [test-check](.claude/skills/test-check/SKILL.md) | 実装完了判定チェックリスト |

### Issue 管理

| スキル | 用途 |
|---|---|
| [start](.claude/skills/start/SKILL.md) | 作業開始時に Issue 確認・ブランチ作成まで一括実行 |
| [create-issue](.claude/skills/create-issue/SKILL.md) | Issue 登録テンプレートと手順 |
