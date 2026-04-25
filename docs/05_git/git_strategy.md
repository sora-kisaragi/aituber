# Git 戦略ドキュメント — aituber

## 採用モデル：GitHub Flow

```
main
 └─ feature/xxx   ← 新機能
 └─ fix/xxx       ← バグ修正
 └─ docs/xxx      ← ドキュメント更新
 └─ refactor/xxx  ← リファクタリング
 └─ chore/xxx     ← 設定変更
```

- `main` は常にデプロイ可能な状態を保つ
- `main` への直接 push 禁止（PR 経由のみ）
- 小さく・頻繁にマージする

---

## ブランチ命名規則

| プレフィックス | 用途 | 例 |
|---|---|---|
| `feature/` | 新機能開発 | `feature/db-schema` |
| `fix/` | バグ修正 | `fix/tts-retry` |
| `docs/` | ドキュメント更新 | `docs/api-reference` |
| `refactor/` | リファクタリング | `refactor/event-service` |
| `chore/` | 設定・依存関係など | `chore/update-deps` |

- 英語・小文字・ハイフン区切り
- 短く・目的が分かる名前にする

---

## コミットメッセージ規則

### フォーマット

```
<type>: <概要（日本語可）>

<本文（任意）>
```

### type 一覧

| type | 意味 |
|---|---|
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `docs` | ドキュメント |
| `refactor` | リファクタリング |
| `chore` | ビルド・設定変更 |
| `test` | テスト追加・修正 |

### 例

```
feat: DBスキーマとAlembicマイグレーション実装
fix: QwenTTSクライアントのリトライ処理を修正
docs: APIリファレンスを更新
test: EventServiceの異常系テストを追加
```

---

## PR（プルリクエスト）ルール

- タイトルはコミットメッセージと同形式
- 本文に「何を・なぜ」を記述する
- 関連 Issue は `Closes #XX` で紐付ける
- セルフマージも PR 経由で行う（履歴のため）
- マージ後はブランチを削除する

---

## 運用フロー

```
1. main から作業ブランチを切る（/new-feature を使う）
   git checkout -b feature/xxx

2. 開発・コミット（pre-commit が自動で ruff を実行）
   git add <files>
   git commit -m "feat: ..."

3. push して PR を作成（/ship を使う）
   git push origin feature/xxx
   gh pr create ...

4. GitHub で PR を main にマージ

5. ブランチ削除
   git branch -d feature/xxx
```

---

## 自走専用フロー（long-run）

長時間作業は、`main` へ直接積まずに自走専用ブランチへ集約する。

```text
main
└─ autopilot/<topic>          ← 自走専用親ブランチ
   ├─ feature/<task-a>        ← 子ブランチA
   ├─ fix/<task-b>            ← 子ブランチB
   └─ ...
```

### 手順

1. `main` から `autopilot/<topic>` を作成
2. 子ブランチを `autopilot/<topic>` から作成して実装
3. 子ブランチを `autopilot/<topic>` に順次マージ
4. すべて完了後に `autopilot/<topic>` から `main` へ PR

### ポイント

- 作業途中の子ブランチは `main` に直接 PR しない
- 最終的なレビュー単位は `autopilot/<topic> -> main` の1本にまとめる
- 進捗通知は Git hooks ではなく Codex hooks（Discord 通知）を使う

---

## タグ・リリース

| タグ形式 | タイミング |
|---|---|
| `v0.1.0` | MVP パイプライン完成 |
| `v0.2.0` | 品質改善フェーズ完成 |
| `v1.0.0` | 本番リリース |

```bash
git tag v0.1.0
git push origin v0.1.0
```
