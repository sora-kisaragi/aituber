#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="パイプライン性能レポートを表示する")
    parser.add_argument("--media-root", default="/var/aituber/media", help="media ルート")
    parser.add_argument("--video-id", default="", help="対象 video_id（省略時は最新）")
    parser.add_argument("--json", action="store_true", help="JSON で出力する")
    return parser.parse_args()


def resolve_perf_path(media_root: str, video_id: str) -> Path:
    root = Path(media_root)
    if video_id:
        path = root / video_id / "debug" / "performance.json"
        if not path.exists():
            raise FileNotFoundError(f"performance.json が見つかりません: {path}")
        return path

    candidates = sorted(
        root.glob("*/debug/performance.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"performance.json が見つかりません: {root}")
    return candidates[0]


def summarize(payload: dict[str, Any]) -> dict[str, Any]:
    steps = payload.get("steps", [])
    sorted_steps = sorted(steps, key=lambda x: float(x.get("elapsed_ms", 0.0)), reverse=True)
    top_steps = sorted_steps[:5]

    memory_growth = [
        {
            "name": step.get("name", ""),
            "rss_growth_mb": round(
                float(step.get("rss_end_mb", 0.0)) - float(step.get("rss_start_mb", 0.0)),
                3,
            ),
        }
        for step in steps
    ]
    top_memory = sorted(memory_growth, key=lambda x: x["rss_growth_mb"], reverse=True)[:5]

    return {
        "video_id": payload.get("video_id"),
        "started_at": payload.get("started_at"),
        "finished_at": payload.get("finished_at"),
        "total_elapsed_ms": payload.get("total_elapsed_ms", 0.0),
        "top_elapsed_steps": top_steps,
        "top_memory_growth_steps": top_memory,
        "summary": payload.get("summary", {}),
    }


def print_text(summary: dict[str, Any]) -> None:
    total_s = float(summary.get("total_elapsed_ms", 0.0)) / 1000
    print(f"video_id: {summary.get('video_id')}")
    print(f"total_elapsed: {total_s:.2f}s")
    print(f"started_at: {summary.get('started_at')}")
    print(f"finished_at: {summary.get('finished_at')}")
    print("")
    print("Top elapsed steps:")
    for step in summary.get("top_elapsed_steps", []):
        elapsed_s = float(step.get("elapsed_ms", 0.0)) / 1000
        print(f"- {step.get('name')}: {elapsed_s:.2f}s ({step.get('status')})")
    print("")
    print("Top memory growth steps:")
    for row in summary.get("top_memory_growth_steps", []):
        print(f"- {row.get('name')}: {row.get('rss_growth_mb', 0.0):.3f}MB")


def main() -> int:
    args = parse_args()
    perf_path = resolve_perf_path(args.media_root, args.video_id)
    payload = json.loads(perf_path.read_text(encoding="utf-8"))
    summary = summarize(payload)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"path: {perf_path}")
        print_text(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
