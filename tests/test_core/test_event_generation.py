from app.core.event_generation import EventService
from app.core.vision import VisionAnalysis


class TestEventService:
    def setup_method(self) -> None:
        self.service = EventService()

    def test_generate_returns_at_least_one_event(self) -> None:
        results = self.service.generate("seg-1", 0.0, [])
        assert len(results) >= 1

    def test_generate_from_analysis(self) -> None:
        analysis = VisionAnalysis(
            scene_summary="戦闘中",
            objects=["敵"],
            actions=["攻撃"],
            ui_state=[],
            confidence=0.9,
        )
        results = self.service.generate("seg-1", 2.5, [analysis])
        assert len(results) == 1
        assert results[0].event_type == "combat"
        assert results[0].speak_recommended is True

    def test_low_importance_not_recommended(self) -> None:
        analysis = VisionAnalysis(
            scene_summary="待機",
            objects=[],
            actions=[],
            ui_state=[],
            confidence=0.2,
        )
        results = self.service.generate("seg-1", 0.0, [analysis])
        assert results[0].speak_recommended is False

    def test_generate_when_kill_keyword_detected_returns_kill_type(self) -> None:
        analysis = VisionAnalysis(
            scene_summary="敵を撃破した",
            objects=["enemy"],
            actions=["kill"],
            ui_state=[],
            confidence=0.5,
        )
        results = self.service.generate("seg-1", 0.0, [analysis])
        assert results[0].event_type == "kill"
        assert results[0].importance > 0.7

    def test_generate_when_death_keyword_detected_returns_death_type(self) -> None:
        analysis = VisionAnalysis(
            scene_summary="プレイヤーがやられた",
            objects=["player"],
            actions=["death"],
            ui_state=[],
            confidence=0.55,
        )
        results = self.service.generate("seg-1", 0.0, [analysis])
        assert results[0].event_type == "death"
        assert results[0].importance >= 0.7

    def test_generate_when_levelup_keyword_detected_returns_level_up_type(self) -> None:
        analysis = VisionAnalysis(
            scene_summary="レベルアップ演出",
            objects=["ui"],
            actions=["level up"],
            ui_state=[],
            confidence=0.52,
        )
        results = self.service.generate("seg-1", 0.0, [analysis])
        assert results[0].event_type == "level_up"
        assert results[0].importance >= 0.65

    def test_emotion_hint_excited_for_high_importance(self) -> None:
        analysis = VisionAnalysis(
            scene_summary="ボス戦",
            objects=["ボス"],
            actions=["攻撃"],
            ui_state=[],
            confidence=0.95,
        )
        results = self.service.generate("seg-1", 0.0, [analysis])
        assert results[0].emotion_hint == "excited"
