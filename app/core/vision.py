"""フレーム解析データの共通型と変換ロジック。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.clients.vlm_client import VLMClient


@dataclass
class VisionAnalysis:
    """1フレーム分の視覚解析結果。"""

    scene_summary: str
    objects: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    ui_state: list[str] = field(default_factory=list)
    confidence: float = 0.8


class VisionService:
    """フレーム画像を解析してシーン情報を返す。"""

    def analyze_frame(
        self,
        image_path: str,
        vlm_client: VLMClient | None = None,
    ) -> VisionAnalysis:
        """フレーム画像のシーン情報を返す。

        Args:
            image_path: 対象フレーム画像パス。
            vlm_client: 指定時は外部VLMで解析し、未指定時は固定ダミー値を返す。

        Returns:
            解析済み `VisionAnalysis`。
        """
        if vlm_client is not None:
            return vlm_client.analyze(image_path)
        return VisionAnalysis(
            scene_summary="戦闘中",
            objects=["敵", "プレイヤー"],
            actions=["攻撃"],
            ui_state=[],
            confidence=0.8,
        )

    def to_dict(self, analysis: VisionAnalysis) -> dict[str, Any]:
        """`VisionAnalysis` を辞書形式へ変換する。

        Args:
            analysis: 変換対象の解析結果。

        Returns:
            DB 保存やJSON出力に使える辞書。
        """
        return {
            "scene_summary": analysis.scene_summary,
            "objects": analysis.objects,
            "actions": analysis.actions,
            "ui_state": analysis.ui_state,
            "confidence": analysis.confidence,
        }
