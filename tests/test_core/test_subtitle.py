"""test_subtitle モジュール。"""

import tempfile
from pathlib import Path

from app.core.subtitle import SubtitleService


class TestSubtitleService:
    """TestSubtitleService テストクラス。"""

    def setup_method(self) -> None:
        """各テストで使う `SubtitleService` を初期化する。

        Args:
            なし。

        Returns:
            なし。各テストで使う `SubtitleService` を初期化する。
        """
        self.service = SubtitleService()

    def test_generate_creates_srt_file(self) -> None:
        """test_generate_creates_srt_file の動作を検証する。

        Args:
            なし。

        Returns:
            なし。SRT ファイル生成と終了時刻計算を検証する。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.service.generate(
                text="こんにちは世界！",
                start_time=0.0,
                duration_seconds=3.0,
                commentary_id="com-1",
                media_root=tmpdir,
            )
            assert Path(result.file_path).exists()
            assert result.end_time == 3.0

    def test_srt_content_contains_text(self) -> None:
        """test_srt_content_contains_text の動作を検証する。

        Args:
            なし。

        Returns:
            なし。SRT 本文にテキストと時間範囲が含まれることを検証する。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.service.generate(
                text="テスト実況",
                start_time=5.0,
                duration_seconds=2.0,
                commentary_id="com-2",
                media_root=tmpdir,
            )
            assert "テスト実況" in result.srt_content
            assert "00:00:05,000" in result.srt_content
            assert "00:00:07,000" in result.srt_content

    def test_long_text_splits_lines(self) -> None:
        """test_long_text_splits_lines の動作を検証する。

        Args:
            なし。

        Returns:
            なし。長文が複数行へ分割されることを検証する。
        """
        long_text = "あ" * 50
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.service.generate(
                text=long_text,
                start_time=0.0,
                duration_seconds=5.0,
                commentary_id="com-3",
                media_root=tmpdir,
            )
            # 50文字 / 20文字 = 3行以上
            assert result.srt_content.count("\n") >= 3
