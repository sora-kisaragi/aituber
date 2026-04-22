from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VisionAnalysis:
    scene_summary: str
    objects: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    ui_state: list[str] = field(default_factory=list)
    confidence: float = 0.8


class VisionService:
    """フレーム画像を解析してシーン情報を返す。MVP ではダミーレスポンスを返す。"""

    def analyze_frame(self, image_path: str) -> VisionAnalysis:
        """フレームのシーン情報を返す。後続イシューで実 VLM に差し替える。"""
        return VisionAnalysis(
            scene_summary="戦闘中",
            objects=["敵", "プレイヤー"],
            actions=["攻撃"],
            ui_state=[],
            confidence=0.8,
        )

    def to_dict(self, analysis: VisionAnalysis) -> dict[str, Any]:
        return {
            "scene_summary": analysis.scene_summary,
            "objects": analysis.objects,
            "actions": analysis.actions,
            "ui_state": analysis.ui_state,
            "confidence": analysis.confidence,
        }
