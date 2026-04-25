"""videos API の動画ID検証ヘルパーを検証する。"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.api.videos import _get_video_or_404, _parse_video_uuid


class _DummyQuery:
    """テスト用の簡易 Query モック。"""

    def __init__(self, result: object | None) -> None:
        """返却結果を受け取って初期化する。"""
        self._result = result

    def filter(self, *_args: object, **_kwargs: object) -> _DummyQuery:
        """filter 呼び出しを透過し、自身を返す。"""
        return self

    def first(self) -> object | None:
        """first の戻り値として初期化時の結果を返す。"""
        return self._result


class _DummySession:
    """テスト用の簡易 Session モック。"""

    def __init__(self, result: object | None) -> None:
        """query().first() で返す結果を保持する。"""
        self._result = result

    def query(self, _model: object) -> _DummyQuery:
        """常に同じ結果を返す Query モックを返却する。"""
        return _DummyQuery(self._result)


def test_parse_video_uuid_when_valid_returns_uuid() -> None:
    """有効UUID文字列を UUID オブジェクトへ変換できることを確認する。"""
    video_id = "40dfddae-d7f8-4e55-847b-ac2279bbf07b"
    parsed = _parse_video_uuid(video_id)
    assert isinstance(parsed, uuid.UUID)
    assert str(parsed) == video_id


def test_parse_video_uuid_when_invalid_raises_404() -> None:
    """不正文字列を 404 として扱うことを確認する。"""
    with pytest.raises(HTTPException) as exc_info:
        _parse_video_uuid("not-a-uuid")
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "動画が見つかりません"


def test_get_video_or_404_when_video_exists_returns_model() -> None:
    """動画が存在する場合にそのまま返却されることを確認する。"""
    video = object()
    db = _DummySession(video)
    resolved = _get_video_or_404(db, "40dfddae-d7f8-4e55-847b-ac2279bbf07b")
    assert resolved is video


def test_get_video_or_404_when_video_missing_raises_404() -> None:
    """動画が存在しない場合に404を送出することを確認する。"""
    db = _DummySession(None)
    with pytest.raises(HTTPException) as exc_info:
        _get_video_or_404(db, "40dfddae-d7f8-4e55-847b-ac2279bbf07b")
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "動画が見つかりません"
