from pathlib import Path
import tempfile

from app.core.subtitle import SubtitleService


class TestSubtitleService:
    def setup_method(self) -> None:
        self.service = SubtitleService()

    def test_generate_creates_srt_file(self) -> None:
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
