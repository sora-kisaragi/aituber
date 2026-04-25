"""動画ごとの進捗状態を一時保持するインメモリストア。"""

from __future__ import annotations

_store: dict[str, dict[str, object]] = {}


def update_progress(video_id: str, step: str, pct: int, message: str = "") -> None:
    """動画進捗を更新する。

    Args:
        video_id: 対象動画ID。
        step: 現在の処理ステップ名。
        pct: 進捗率（0-100想定）。
        message: 進捗表示用メッセージ。

    Returns:
        なし。`_store` に最新進捗を上書き保存する。
    """
    _store[video_id] = {"step": step, "pct": pct, "message": message}


def get_progress(video_id: str) -> dict[str, object] | None:
    """動画進捗を取得する。

    Args:
        video_id: 対象動画ID。

    Returns:
        保存済み進捗辞書。未登録の場合は `None`。
    """
    return _store.get(video_id)


def clear_progress(video_id: str) -> None:
    """動画進捗を削除する。

    Args:
        video_id: 対象動画ID。

    Returns:
        なし。対象動画の進捗がなければ何もしない。
    """
    _store.pop(video_id, None)
