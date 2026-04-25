# テスト記録

このディレクトリには各機能の動作確認結果を記録する。

## ディレクトリ構成

```
06_test/
├── pipeline/     # エンドツーエンドテスト記録
├── core/         # コアロジック単体テスト記録
└── clients/      # 外部 API クライアントテスト記録
```

## 記録方法

テスト実施後は `/test-check` スキルのテンプレートに従って `TC_<機能名>.md` を作成する。

詳細: [テスト・レビュー規約](../03_standards/test_review_standard.md)

## 関連ドキュメント

- [パフォーマンス検証手順](./performance_validation.md)
