"""test_segmentation モジュール。"""

from unittest.mock import MagicMock, patch

from app.core.segmentation import SegmentationService, SegmentResult


class TestSegmentationService:
    """TestSegmentationService テストクラス。"""

    def setup_method(self) -> None:
        """各テストで使う `SegmentationService` を初期化する。

        Args:
            なし。

        Returns:
            なし。各テストで使う `SegmentationService` を準備する。
        """
        self.service = SegmentationService(segment_duration=5, media_root="/tmp/aituber_test")

    @patch("app.core.segmentation.SegmentationService._probe_duration")
    @patch("app.core.segmentation.SegmentationService._cut_segment")
    def test_execute_splits_correctly(self, mock_cut: MagicMock, mock_probe: MagicMock) -> None:
        """test_execute_splits_correctly の動作を検証する。

        Args:
            mock_cut: セグメント切り出し呼び出しを抑止するモック。
            mock_probe: 動画長取得結果を固定するモック。

        Returns:
            なし。分割境界が期待通りであることを検証する。
        """
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
        """test_execute_exact_duration の動作を検証する。

        Args:
            mock_cut: セグメント切り出し呼び出しを抑止するモック。
            mock_probe: 動画長取得結果を固定するモック。

        Returns:
            なし。動画長がちょうど分割単位のときの件数を検証する。
        """
        mock_probe.return_value = 10.0
        results = self.service.execute("/fake/video.mp4", "vid")
        assert len(results) == 2
        assert all(isinstance(r, SegmentResult) for r in results)

    @patch("app.core.segmentation.SegmentationService._probe_duration")
    @patch("app.core.segmentation.SegmentationService._cut_segment")
    def test_segment_type_is_gameplay(self, mock_cut: MagicMock, mock_probe: MagicMock) -> None:
        """test_segment_type_is_gameplay の動作を検証する。

        Args:
            mock_cut: セグメント切り出し呼び出しを抑止するモック。
            mock_probe: 動画長取得結果を固定するモック。

        Returns:
            なし。生成セグメントの既定種別が `gameplay` であることを検証する。
        """
        mock_probe.return_value = 5.0
        results = self.service.execute("/fake/video.mp4", "vid")
        assert results[0].segment_type == "gameplay"
