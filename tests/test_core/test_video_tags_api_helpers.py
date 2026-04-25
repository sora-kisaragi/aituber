"""タグAPI補助関数の正規化・状態更新ロジックを検証する。"""

from types import SimpleNamespace

import pytest

from app.api.videos import _resolve_tts_speaker
from app.core.tags import (
    build_tag_source_map,
    mark_llm_tag_status_skipped,
    normalize_video_metadata,
)
from app.core.video_tagging import refresh_llm_tags


def test_mark_llm_tag_status_skipped_when_called_sets_skipped_status_and_error() -> None:
    """LLM スキップ状態が正しく設定されることを確認する。

    Args:
        なし。

    Returns:
        なし。`llm=skipped` と既定エラーメッセージを検証する。
    """
    metadata = {
        "tags_auto_llm": ["game:zelda"],
        "tag_status": {"rule": "ready", "llm": "pending", "llm_error": None},
    }

    refreshed = mark_llm_tag_status_skipped(metadata)

    assert refreshed["tags_auto_llm"] == ["game:zelda"]
    assert refreshed["tag_status"]["rule"] == "ready"
    assert refreshed["tag_status"]["llm"] == "skipped"
    assert refreshed["tag_status"]["llm_error"] == "LLMTagger 未実装のためスキップしました"


def test_build_tag_source_map_when_tags_exist_returns_expected_sources() -> None:
    """タグソースマップが期待通りに構築されることを確認する。

    Args:
        なし。

    Returns:
        なし。タグ種別ごとの source 判定を検証する。
    """
    metadata = {
        "tags_manual": ["genre:rpg"],
        "tags_auto_rule": ["cfg:tts_mode:custom_voice"],
        "tags_auto_llm": ["game:elden_ring"],
        "tags_suggested_llm": ["candidate:dragon_quest"],
    }

    source_map = build_tag_source_map(metadata)

    assert source_map["genre:rpg"] == "manual"
    assert source_map["cfg:tts_mode:custom_voice"] == "rule"
    assert source_map["game:elden_ring"] == "llm"
    assert source_map["candidate:dragon_quest"] == "llm_suggested"


def test_normalize_video_metadata_when_metadata_is_none_returns_default_structure() -> None:
    """None 入力時に既定構造へ正規化されることを確認する。

    Args:
        なし。

    Returns:
        なし。欠損入力時の既定構造を検証する。
    """
    result = normalize_video_metadata(None)

    assert result["tags_manual"] == []
    assert result["tags_auto_rule"] == []
    assert result["tags_auto_llm"] == []
    assert result["tags_suggested_llm"] == []
    assert result["tags_effective"] == []
    assert result["tag_status"] == {"rule": "pending", "llm": "pending", "llm_error": None}


def test_refresh_llm_tags_when_success_sets_ready_and_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM タグ生成成功時に ready 状態とタグが保存されることを確認する。

    Args:
        monkeypatch: `LLMTagger.generate` を差し替えるための pytest fixture。

    Returns:
        なし。成功時に `tag_status.llm=ready` になることを検証する。
    """

    def fake_generate(
        self, *, video_title: str, current_tags: list[str], llm_client: object
    ) -> dict:
        """LLMTagger のモック実装（成功系）。

        Args:
            video_title: 生成対象動画タイトル。
            current_tags: 既存タグ（プロンプト入力）一覧。
            llm_client: 呼び出し元から渡される LLM クライアント（ダミー）。

        Returns:
            テスト用に固定した LLM タグ生成結果。
        """
        assert video_title == "sample"
        assert "genre:action" in current_tags
        return {
            "tags_auto_llm": ["game:elden_ring"],
            "tags_suggested_llm": ["candidate:dragon_quest"],
        }

    monkeypatch.setattr("app.core.llm_tagger.LLMTagger.generate", fake_generate)
    result = refresh_llm_tags(
        video_id="video-1",
        video_title="sample",
        raw_metadata={"tags_manual": ["genre:action"]},
        llm_client=object(),
    )

    assert result["tags_auto_llm"] == ["game:elden_ring"]
    assert result["tags_suggested_llm"] == ["candidate:dragon_quest"]
    assert result["tag_status"]["llm"] == "ready"
    assert result["tag_status"]["llm_error"] is None


def test_refresh_llm_tags_when_failure_sets_error_and_keeps_existing_tags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM タグ生成失敗時に既存タグ維持と error 状態が設定されることを確認する。

    Args:
        monkeypatch: `LLMTagger.generate` を失敗スタブへ差し替える fixture。

    Returns:
        なし。失敗時に既存タグ維持と `llm=error` を検証する。
    """

    def fake_generate(
        self, *, video_title: str, current_tags: list[str], llm_client: object
    ) -> dict:
        """LLMTagger のモック実装（失敗系）。

        Args:
            video_title: 生成対象動画タイトル。
            current_tags: 既存タグ（未使用だが署名互換のため受け取る）。
            llm_client: 呼び出し元から渡される LLM クライアント（ダミー）。

        Returns:
            返却前に例外を送出するため実際には返らない想定の辞書型。
        """
        raise RuntimeError("timeout")

    monkeypatch.setattr("app.core.llm_tagger.LLMTagger.generate", fake_generate)
    result = refresh_llm_tags(
        video_id="video-2",
        video_title="sample",
        raw_metadata={
            "tags_auto_llm": ["game:street_fighter"],
            "tags_suggested_llm": ["candidate:tekken"],
            "tag_status": {"rule": "ready", "llm": "pending", "llm_error": None},
        },
        llm_client=object(),
    )

    assert result["tags_auto_llm"] == ["game:street_fighter"]
    assert result["tags_suggested_llm"] == ["candidate:tekken"]
    assert result["tag_status"]["llm"] == "error"
    assert result["tag_status"]["llm_error"] == "timeout"


def test_resolve_tts_speaker_when_style_specific_speaker_exists_returns_style_speaker() -> None:
    """スタイル別話者設定が優先されることを確認する。

    Args:
        なし。

    Returns:
        なし。スタイル別話者の優先解決を検証する。
    """
    cfg = SimpleNamespace(
        tts_default_speaker="base_voice",
        tts_speaker_excited="voice_excited",
        tts_speaker_neutral="voice_neutral",
        tts_speaker_calm="",
    )
    assert _resolve_tts_speaker("excited", cfg) == "voice_excited"
    assert _resolve_tts_speaker("neutral", cfg) == "voice_neutral"
    assert _resolve_tts_speaker("calm", cfg) == "base_voice"
