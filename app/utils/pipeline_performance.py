"""パイプライン性能計測（時間・メモリ）ユーティリティ。"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from app.utils.logging import logger

try:
    import resource
except Exception:  # pragma: no cover - Windows 互換
    resource = None


def _rss_mb() -> float:
    """現在プロセスの最大RSSをMB単位で返す。

    Args:
        なし。

    Returns:
        MB 単位の RSS 値。非対応環境では `0.0`。
    """
    if resource is None:
        return 0.0
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return round(usage / (1024 * 1024), 3)
    return round(usage / 1024, 3)


class PipelinePerformanceRecorder:
    """パイプライン性能（時間・メモリ）をステップ単位で記録する。"""

    def __init__(self, media_root: str, video_id: str) -> None:
        """性能記録の出力先を初期化する。

        Args:
            media_root: メディア保存ルート。
            video_id: 対象動画ID。

        Returns:
            なし。`performance.json` の保存先を確定する。
        """
        self.video_id = video_id
        self._started_at = datetime.now(tz=UTC)
        self._started_perf = perf_counter()
        self._steps: list[dict[str, Any]] = []
        self._checkpoints: list[dict[str, Any]] = []
        self._path = Path(media_root) / video_id / "debug" / "performance.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def measure(
        self,
        step_name: str,
        input_data: dict[str, Any] | None = None,
    ) -> Iterator[None]:
        """ステップ実行時間・メモリを計測するコンテキストマネージャー。

        Args:
            step_name: 記録するステップ名。
            input_data: 補助入力情報。

        Yields:
            呼び出し側の処理コンテキスト。

        Returns:
            ステップ計測を行うコンテキストマネージャー。
        """
        started_at = datetime.now(tz=UTC)
        started_perf = perf_counter()
        rss_start_mb = _rss_mb()
        error_message: str | None = None
        try:
            yield
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            elapsed_ms = round((perf_counter() - started_perf) * 1000, 3)
            step = {
                "name": step_name,
                "status": "error" if error_message else "ok",
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(tz=UTC).isoformat(),
                "elapsed_ms": elapsed_ms,
                "rss_start_mb": rss_start_mb,
                "rss_end_mb": _rss_mb(),
                "input": input_data or {},
            }
            if error_message:
                step["error"] = error_message
            self._steps.append(step)
            self._save()

    def checkpoint(self, label: str, payload: dict[str, Any] | None = None) -> None:
        """任意タイミングのスナップショットを記録する。

        Args:
            label: チェックポイント名。
            payload: 補助情報。

        Returns:
            なし。現在時点のメトリクスを中間記録する。
        """
        elapsed_ms = round((perf_counter() - self._started_perf) * 1000, 3)
        self._checkpoints.append(
            {
                "label": label,
                "recorded_at": datetime.now(tz=UTC).isoformat(),
                "elapsed_ms": elapsed_ms,
                "rss_mb": _rss_mb(),
                "payload": payload or {},
            }
        )
        self._save()

    def finalize(self, summary: dict[str, Any] | None = None) -> str | None:
        """性能レポートをJSONとして保存する。

        Args:
            summary: 最終サマリー情報。

        Returns:
            保存成功時はファイルパス、失敗時は `None`。
        """
        total_elapsed_ms = round((perf_counter() - self._started_perf) * 1000, 3)
        payload = {
            "video_id": self.video_id,
            "started_at": self._started_at.isoformat(),
            "finished_at": datetime.now(tz=UTC).isoformat(),
            "total_elapsed_ms": total_elapsed_ms,
            "steps": self._steps,
            "checkpoints": self._checkpoints,
            "summary": summary or {},
            "top_elapsed_steps": self._top_elapsed_steps(),
        }
        try:
            self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
        except Exception as e:
            logger.error("performance 記録保存失敗: %s", e)
            return None
        logger.debug("performance 記録保存: %s", self._path)
        return str(self._path)

    def _save(self) -> None:
        """現在の計測内容を中間保存する。"""
        self.finalize()

    def _top_elapsed_steps(self) -> list[dict[str, Any]]:
        """経過時間が長いステップ上位5件を返す。

        Args:
            なし。

        Returns:
            経過時間降順の上位 5 ステップ配列。
        """
        ranked = sorted(
            self._steps, key=lambda row: float(row.get("elapsed_ms", 0.0)), reverse=True
        )
        return ranked[:5]
