"""test_composer モジュール。"""

from app.core.composer import AudioEntry, Composer


class TestComposer:
    """TestComposer テストクラス。"""

    def test_schedule_entries_shifts_overlap(self) -> None:
        """test_schedule_entries_shifts_overlap の動作を検証する。

        Args:
            なし。

        Returns:
            なし。重複入力時の開始時刻シフトを検証する。
        """
        composer = Composer()
        entries = [
            AudioEntry(audio_path="a.wav", start_time=0.0, duration_seconds=2.0),
            AudioEntry(audio_path="b.wav", start_time=1.0, duration_seconds=1.5),
        ]

        normalized = composer.schedule_entries(entries)

        assert len(normalized) == 2
        assert normalized[0].start_time == 0.0
        assert normalized[1].start_time == 2.0

    def test_schedule_entries_respects_min_gap(self) -> None:
        """test_schedule_entries_respects_min_gap の動作を検証する。

        Args:
            なし。

        Returns:
            なし。`min_gap_seconds` が反映されることを検証する。
        """
        composer = Composer()
        entries = [
            AudioEntry(audio_path="a.wav", start_time=0.0, duration_seconds=1.0),
            AudioEntry(audio_path="b.wav", start_time=0.5, duration_seconds=1.0),
        ]

        normalized = composer.schedule_entries(entries, min_gap_seconds=0.5)

        assert len(normalized) == 2
        assert normalized[0].start_time == 0.0
        assert normalized[1].start_time == 1.5
