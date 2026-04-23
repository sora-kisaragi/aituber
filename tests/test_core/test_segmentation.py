from unittest.mock import MagicMock, patch

from app.core.segmentation import SegmentationService, SegmentResult


class TestSegmentationService:
    def setup_method(self) -> None:
        self.service = SegmentationService(segment_duration=5, media_root="/tmp/aituber_test")

    @patch("app.core.segmentation.SegmentationService._probe_duration")
    @patch("app.core.segmentation.SegmentationService._cut_segment")
    def test_execute_splits_correctly(self, mock_cut: MagicMock, mock_probe: MagicMock) -> None:
        mock_probe.return_value = 13.0
        results = self.service.execute("/fake/video.mp4", "test-video-id")

        assert len(results) == 3
        assert results[0].start_time == 0.0
        assert results[0].end_time == 5.0
        assert results[1].start_time == 5.0
        assert results[1].end_time == 10.0
        assert results[2].start_time == 10.0
        assert results[2].end_time == 13.0

    @patch("app.core.segmentation.SegmentationService._probe_duration")
    @patch("app.core.segmentation.SegmentationService._cut_segment")
    def test_execute_exact_duration(self, mock_cut: MagicMock, mock_probe: MagicMock) -> None:
        mock_probe.return_value = 10.0
        results = self.service.execute("/fake/video.mp4", "vid")
        assert len(results) == 2
        assert all(isinstance(r, SegmentResult) for r in results)

    @patch("app.core.segmentation.SegmentationService._probe_duration")
    @patch("app.core.segmentation.SegmentationService._cut_segment")
    def test_segment_type_is_gameplay(self, mock_cut: MagicMock, mock_probe: MagicMock) -> None:
        mock_probe.return_value = 5.0
        results = self.service.execute("/fake/video.mp4", "vid")
        assert results[0].segment_type == "gameplay"
