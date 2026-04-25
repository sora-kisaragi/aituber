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

    def test_schedule_entries_clip_previous_trims_old_entry(self) -> None:
        """test_schedule_entries_clip_previous_trims_old_entry の動作を検証する。

        Args:
            なし。

        Returns:
            なし。`clip_previous` で前発話が短縮されることを検証する。
        """
        composer = Composer()
        entries = [
            AudioEntry(audio_path="a.wav", start_time=0.0, duration_seconds=3.0),
            AudioEntry(audio_path="b.wav", start_time=1.0, duration_seconds=2.0),
        ]

        normalized = composer.schedule_entries(entries, overlap_strategy="clip_previous")

        assert len(normalized) == 2
        assert normalized[0].start_time == 0.0
        assert normalized[0].duration_seconds == 1.0
        assert normalized[1].start_time == 1.0
        assert normalized[1].duration_seconds == 2.0

    def test_schedule_entries_clip_previous_drops_too_short_tail(self) -> None:
        """test_schedule_entries_clip_previous_drops_too_short_tail の動作を検証する。

        Args:
            なし。

        Returns:
            なし。最小保持秒未満の前発話は破棄されることを検証する。
        """
        composer = Composer()
        entries = [
            AudioEntry(audio_path="a.wav", start_time=0.0, duration_seconds=3.0),
            AudioEntry(audio_path="b.wav", start_time=0.2, duration_seconds=1.0),
        ]

        normalized = composer.schedule_entries(
            entries,
            overlap_strategy="clip_previous",
            min_keep_duration_seconds=0.5,
        )

        assert len(normalized) == 2
        assert normalized[0].duration_seconds == 0.0
        assert normalized[1].start_time == 0.2

    def test_schedule_entries_clip_previous_respects_min_gap(self) -> None:
        """test_schedule_entries_clip_previous_respects_min_gap の動作を検証する。

        Args:
            なし。

        Returns:
            なし。`clip_previous` 時にも最小ギャップが反映されることを検証する。
        """
        composer = Composer()
        entries = [
            AudioEntry(audio_path="a.wav", start_time=0.0, duration_seconds=3.0),
            AudioEntry(audio_path="b.wav", start_time=1.5, duration_seconds=1.0),
        ]

        normalized = composer.schedule_entries(
            entries,
            overlap_strategy="clip_previous",
            min_gap_seconds=0.5,
        )

        assert len(normalized) == 2
        assert normalized[0].duration_seconds == 1.0
        assert normalized[1].start_time == 1.5
