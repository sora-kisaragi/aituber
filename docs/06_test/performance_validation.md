# パフォーマンス検証手順

Issue: #21

## 目的

- 10分動画のエンドツーエンド処理時間を計測する
- ステップ別の処理時間とメモリ増分を記録する
- ボトルネック候補をレポート化する

## 手順

1. パイプラインを実行する

```bash
.venv/bin/python scripts/run_pipeline.py \
  --input sample_data/videos/<10min-video>.mp4 \
  --title "perf-10min"
```

2. レポートを表示する（最新実行）

```bash
.venv/bin/python scripts/perf_report.py --media-root /var/aituber/media
```

3. JSON レポートとして保存する

```bash
.venv/bin/python scripts/perf_report.py --media-root /var/aituber/media --json > perf_report.json
```

## 生成物

- `media/<video_id>/debug/performance.json`
  - 総処理時間
  - ステップ別 elapsed / RSS
  - チェックポイント
- `scripts/perf_report.py` の出力
  - `Top elapsed steps`
  - `Top memory growth steps`

## 判定観点

- 前回計測と比較して、`total_elapsed_ms` が悪化していないか
- `top_elapsed_steps` 上位が想定通りか（例: `segment_pipeline`, `commentary_generation`）
- `top_memory_growth_steps` が同一箇所に偏り続けていないか
