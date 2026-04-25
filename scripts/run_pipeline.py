"""
エンドツーエンドパイプラインスクリプト。

使い方:
    python scripts/run_pipeline.py --input sample.mp4 [--title "タイトル"]
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path
from typing import Any

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
from sqlalchemy.orm import Session

from app.clients.llm_client import LLMClient
from app.clients.qwen_tts_client import QwenTTSClient
from app.config.config import settings
from app.core.composer import AudioEntry, Composer
from app.core.event_generation import EventService
from app.core.planning import UtterancePlanner
from app.core.prompt import CommentaryService
from app.core.segmentation import FrameExtractor, SegmentationService
from app.core.subtitle import SubtitleService
from app.core.vision import VisionService
from app.db.session import SessionLocal
from app.models.models import (
    Audio,
    Commentary,
    Event,
    Frame,
    Segment,
    Subtitle,
    UtterancePlan,
    Video,
)
from app.utils.logging import logger
from app.utils.pipeline_debug import PipelineDebugRecorder
from app.utils.pipeline_performance import PipelinePerformanceRecorder

_STYLE_INSTRUCT: dict[str, str] = {
    "excited": (
        "Speak with high energy and excitement, "
        "like a passionate game streamer at a climactic moment."
    ),
    "neutral": "Speak in a natural, conversational voice like a friendly game commentator.",
    "calm": "Speak slowly and calmly in a relaxed, gentle voice with low energy.",
}


def probe_video_meta(video_path: str) -> tuple[float, float]:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    return frames / fps, fps


def run(input_path: str, title: str) -> str:
    db: Session = SessionLocal()
    try:
        return _run_pipeline(db, input_path, title)
    finally:
        db.close()


def _run_pipeline(db: Session, input_path: str, title: str) -> str:
    logger.info("=== パイプライン開始: %s ===", input_path)

    video_id = uuid.uuid4()
    media_dir = Path(settings.media_root) / str(video_id)
    media_dir.mkdir(parents=True, exist_ok=True)
    debug_recorder = PipelineDebugRecorder(settings.media_root, str(video_id))
    perf_recorder = PipelinePerformanceRecorder(settings.media_root, str(video_id))
    perf_recorder.checkpoint(
        "pipeline_started",
        payload={"input_path": input_path, "title": title},
    )

    # ── 動画登録 ──────────────────────────────────────────────────────────────
    with perf_recorder.measure("video_registration", {"input_path": input_path}):
        dest_path = media_dir / Path(input_path).name
        import shutil

        shutil.copy2(input_path, dest_path)

        duration, fps = probe_video_meta(str(dest_path))
        video = Video(
            id=video_id,
            title=title or Path(input_path).stem,
            duration_seconds=duration,
            fps=fps,
            storage_path=str(dest_path),
        )
        db.add(video)
        db.commit()
        debug_recorder.save_step_io(
            "video_registration",
            input_data={
                "input_path": input_path,
                "title": title,
            },
            output_data={
                "video_id": str(video_id),
                "storage_path": str(dest_path),
                "duration_seconds": duration,
                "fps": fps,
            },
        )
    logger.info("動画登録完了: video_id=%s duration=%.1fs", video_id, duration)

    # ── 動画分割 ──────────────────────────────────────────────────────────────
    seg_service = SegmentationService(
        segment_duration=settings.segment_duration,
        media_root=settings.media_root,
    )
    with perf_recorder.measure(
        "segmentation",
        {"segment_duration": settings.segment_duration},
    ):
        seg_results = seg_service.execute(str(dest_path), str(video_id))
        debug_recorder.save_step_io(
            "segmentation",
            input_data={
                "video_path": str(dest_path),
                "segment_duration": settings.segment_duration,
            },
            output_data={
                "segment_count": len(seg_results),
                "segments": [
                    {
                        "index": idx,
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "segment_type": seg.segment_type,
                        "storage_path": seg.storage_path,
                    }
                    for idx, seg in enumerate(seg_results)
                ],
            },
        )
    logger.info("分割完了: %d セグメント", len(seg_results))

    # ── フレーム抽出・VLM 解析・イベント生成 ──────────────────────────────────
    frame_extractor = FrameExtractor(media_root=settings.media_root)
    vision_service = VisionService()
    event_service = EventService()

    all_event_results = []
    segment_debug_summaries: list[dict[str, Any]] = []

    with perf_recorder.measure("segment_pipeline", {"segment_count": len(seg_results)}):
        for seg_idx, seg_result in enumerate(seg_results):
            logger.debug(
                "segment処理開始: video_id=%s index=%d/%d range=%.2f-%.2f",
                video_id,
                seg_idx + 1,
                len(seg_results),
                seg_result.start_time,
                seg_result.end_time,
            )
            segment = Segment(
                video_id=video.id,
                start_time=seg_result.start_time,
                end_time=seg_result.end_time,
                segment_type=seg_result.segment_type,
                storage_path=seg_result.storage_path,
            )
            db.add(segment)
            db.flush()
            debug_recorder.append_segment_debug(
                segment_index=seg_idx,
                segment_id=str(segment.id),
                stage="segment_init",
                input_data={
                    "start_time": seg_result.start_time,
                    "end_time": seg_result.end_time,
                    "segment_type": seg_result.segment_type,
                },
                output_data={"segment_storage_path": seg_result.storage_path},
            )

            frame_results = frame_extractor.extract(
                str(dest_path),
                str(segment.id),
                seg_result.start_time,
                seg_result.end_time,
            )
            frame_debug_rows = [
                {"timestamp": fr.timestamp, "image_path": fr.image_path} for fr in frame_results
            ]
            debug_recorder.append_segment_debug(
                segment_index=seg_idx,
                segment_id=str(segment.id),
                stage="frame_extraction",
                input_data={
                    "video_path": str(dest_path),
                    "start_time": seg_result.start_time,
                    "end_time": seg_result.end_time,
                },
                output_data={
                    "frame_count": len(frame_results),
                    "frames": frame_debug_rows,
                },
            )

            analyses = []
            analysis_debug_rows: list[dict[str, Any]] = []
            for fr in frame_results:
                analysis = vision_service.analyze_frame(fr.image_path)
                features = vision_service.to_dict(analysis)
                frame = Frame(
                    segment_id=segment.id,
                    timestamp=fr.timestamp,
                    image_path=fr.image_path,
                    features=features,
                )
                db.add(frame)
                analyses.append(analysis)
                analysis_debug_rows.append(
                    {
                        "timestamp": fr.timestamp,
                        "image_path": fr.image_path,
                        "analysis": features,
                    }
                )
            debug_recorder.append_segment_debug(
                segment_index=seg_idx,
                segment_id=str(segment.id),
                stage="vision_analysis",
                input_data={"frame_count": len(frame_results)},
                output_data={
                    "analysis_count": len(analysis_debug_rows),
                    "analyses": analysis_debug_rows,
                },
            )

            event_results = event_service.generate(str(segment.id), seg_result.start_time, analyses)
            event_debug_rows: list[dict[str, Any]] = []
            for er in event_results:
                event = Event(
                    segment_id=segment.id,
                    timestamp=er.timestamp,
                    event_type=er.event_type,
                    importance=er.importance,
                    details=er.details,
                )
                db.add(event)
                event_debug_rows.append(
                    {
                        "event_id": er.event_id,
                        "timestamp": er.timestamp,
                        "event_type": er.event_type,
                        "importance": er.importance,
                        "emotion_hint": er.emotion_hint,
                        "speak_recommended": er.speak_recommended,
                        "details": er.details,
                    }
                )
            debug_recorder.append_segment_debug(
                segment_index=seg_idx,
                segment_id=str(segment.id),
                stage="event_generation",
                input_data={
                    "analysis_count": len(analysis_debug_rows),
                    "segment_start_time": seg_result.start_time,
                },
                output_data={
                    "event_count": len(event_debug_rows),
                    "events": event_debug_rows,
                },
            )
            segment_debug_summaries.append(
                {
                    "segment_index": seg_idx,
                    "segment_id": str(segment.id),
                    "start_time": seg_result.start_time,
                    "end_time": seg_result.end_time,
                    "frame_count": len(frame_results),
                    "analysis_count": len(analysis_debug_rows),
                    "event_count": len(event_debug_rows),
                }
            )
            perf_recorder.checkpoint(
                "segment_processed",
                payload={
                    "segment_index": seg_idx,
                    "frame_count": len(frame_results),
                    "event_count": len(event_results),
                },
            )
            logger.debug(
                "segment処理完了: video_id=%s segment_id=%s frames=%d events=%d",
                video_id,
                segment.id,
                len(frame_results),
                len(event_debug_rows),
            )
            all_event_results.extend(event_results)

        db.commit()
        debug_recorder.save_step_io(
            "segment_pipeline",
            input_data={"segment_count": len(seg_results)},
            output_data={
                "total_event_count": len(all_event_results),
                "segments": segment_debug_summaries,
            },
        )
    logger.info("イベント生成完了: %d 件", len(all_event_results))

    # ── 発話計画 ──────────────────────────────────────────────────────────────
    planner = UtterancePlanner()
    with perf_recorder.measure("planning", {"event_count": len(all_event_results)}):
        plan_results = planner.plan(str(video.id), all_event_results)
        debug_recorder.save_step_io(
            "planning",
            input_data={"event_count": len(all_event_results)},
            output_data={
                "plan_count": len(plan_results),
                "plans": [
                    {
                        "plan_id": pr.plan_id,
                        "event_ids": pr.event_ids,
                        "start_time": pr.start_time,
                        "end_time": pr.end_time,
                        "priority": pr.priority,
                        "style": pr.style,
                    }
                    for pr in plan_results
                ],
            },
        )
    logger.info("発話計画: %d 件", len(plan_results))

    # ── LLM 実況生成 ──────────────────────────────────────────────────────────
    llm_client = LLMClient(
        base_url=settings.llm_api_base,
        api_key=settings.llm_api_key,
        model=settings.llm_model_name,
    )
    commentary_service = CommentaryService()
    prev_text = ""
    commentary_debug_rows: list[dict[str, Any]] = []

    with perf_recorder.measure("commentary_generation", {"plan_count": len(plan_results)}):
        for plan_idx, pr in enumerate(plan_results):
            plan = UtterancePlan(
                video_id=video.id,
                event_ids=pr.event_ids,
                start_time=pr.start_time,
                end_time=pr.end_time,
                priority=pr.priority,
                style=pr.style,
            )
            db.add(plan)
            db.flush()

            relevant = [e for e in all_event_results if e.event_id in pr.event_ids]
            com_data = commentary_service.generate(pr, relevant, llm_client, prev_text)
            commentary = Commentary(
                utterance_plan_id=plan.id,
                language=com_data["language"],
                style=com_data["style"],
                text=com_data["text"],
                llm_raw_response=com_data["llm_raw_response"],
            )
            db.add(commentary)
            commentary_debug_rows.append(
                {
                    "index": plan_idx,
                    "plan_id": str(plan.id),
                    "event_ids": pr.event_ids,
                    "style": com_data["style"],
                    "text": com_data["text"],
                    "language": com_data["language"],
                }
            )
            prev_text = com_data["text"]
            logger.info("実況生成: [%s] %s", pr.style, com_data["text"][:40])

        db.commit()
        debug_recorder.save_step_io(
            "commentary_generation",
            input_data={"plan_count": len(plan_results)},
            output_data={
                "commentary_count": len(commentary_debug_rows),
                "commentaries": commentary_debug_rows,
            },
        )

    # ── TTS 音声生成 + 字幕生成 ──────────────────────────────────────────────
    tts_client = QwenTTSClient(
        base_url=settings.tts_base_url,
        default_mode=settings.tts_default_mode,
        default_speaker=settings.tts_default_speaker,
        default_language=settings.tts_default_language,
        default_instruct=settings.tts_default_instruct,
    )
    subtitle_service = SubtitleService()

    plans_in_db = (
        db.query(UtterancePlan)
        .filter(UtterancePlan.video_id == str(video.id))
        .order_by(UtterancePlan.start_time)
        .all()
    )

    audio_entries: list[AudioEntry] = []
    srt_paths: list[str] = []

    with perf_recorder.measure("tts_and_subtitle", {"plan_count": len(plans_in_db)}):
        for plan in plans_in_db:
            commentary = (
                db.query(Commentary).filter(Commentary.utterance_plan_id == plan.id).first()
            )
            if not commentary:
                continue

            audio_path = str(Path(settings.media_root) / str(commentary.id) / "audio.wav")
            speaker = _resolve_tts_speaker(commentary.style or "")
            instruct = _STYLE_INSTRUCT.get(commentary.style or "", "")
            try:
                duration_sec = tts_client.synthesize(
                    commentary.text,
                    audio_path,
                    speaker=speaker,
                    instruct=instruct,
                )
            except RuntimeError as exc:
                logger.warning("TTS 失敗 (スキップ): %s", exc)
                continue

            audio = Audio(
                commentary_id=commentary.id,
                tts_mode=settings.tts_default_mode,
                speaker=speaker,
                language=settings.tts_default_language,
                storage_path=audio_path,
                duration_seconds=duration_sec,
            )
            db.add(audio)

            srt_result = subtitle_service.generate(
                commentary.text,
                plan.start_time,
                duration_sec,
                str(commentary.id),
                settings.media_root,
            )
            subtitle = Subtitle(
                commentary_id=commentary.id,
                file_path=srt_result.file_path,
                start_time=srt_result.start_time,
                end_time=srt_result.end_time,
            )
            db.add(subtitle)

            audio_entries.append(
                AudioEntry(
                    audio_path=audio_path,
                    start_time=plan.start_time,
                    duration_seconds=duration_sec,
                )
            )
            srt_paths.append(srt_result.file_path)

        db.commit()
        debug_recorder.save_step_io(
            "tts_and_subtitle",
            input_data={"plan_count": len(plans_in_db)},
            output_data={
                "audio_count": len(audio_entries),
                "subtitle_count": len(srt_paths),
                "srt_paths": srt_paths,
            },
        )
    logger.info("音声・字幕生成完了: %d 件", len(audio_entries))

    # ── 動画合成 ──────────────────────────────────────────────────────────────
    with perf_recorder.measure("compose", {"audio_count": len(audio_entries)}):
        merged_srt = _merge_srt(srt_paths, str(video_id), settings.media_root)
        output_path = str(media_dir / "output.mp4")
        composer = Composer(media_root=settings.media_root)
        composer.compose(str(dest_path), audio_entries, merged_srt, output_path)
        debug_recorder.save_step_io(
            "compose",
            input_data={
                "input_video": str(dest_path),
                "audio_count": len(audio_entries),
                "merged_srt": merged_srt,
            },
            output_data={"output_path": output_path},
        )

    logger.info("=== パイプライン完了: %s ===", output_path)
    perf_recorder.finalize(
        {
            "segment_count": len(seg_results),
            "event_count": len(all_event_results),
            "plan_count": len(plan_results),
            "audio_count": len(audio_entries),
            "output_path": output_path,
        }
    )
    return output_path


def _merge_srt(srt_paths: list[str], video_id: str, media_root: str) -> str | None:
    valid = [p for p in srt_paths if Path(p).exists()]
    if not valid:
        return None
    merged = Path(media_root) / video_id / "merged.srt"
    with open(merged, "w", encoding="utf-8") as out:
        for p in valid:
            out.write(Path(p).read_text(encoding="utf-8"))
    return str(merged)


def _resolve_tts_speaker(style: str) -> str:
    speaker_map = {
        "excited": settings.tts_speaker_excited.strip(),
        "neutral": settings.tts_speaker_neutral.strip(),
        "calm": settings.tts_speaker_calm.strip(),
    }
    return speaker_map.get((style or "").strip().lower()) or settings.tts_default_speaker


def main() -> None:
    parser = argparse.ArgumentParser(description="AITuber パイプライン実行")
    parser.add_argument("--input", required=True, help="入力 mp4 ファイルパス")
    parser.add_argument("--title", default="", help="動画タイトル（省略時はファイル名）")
    args = parser.parse_args()

    if not Path(args.input).exists():
        logger.error("入力ファイルが見つかりません: %s", args.input)
        sys.exit(1)

    output = run(args.input, args.title)
    print(f"出力: {output}")


if __name__ == "__main__":
    main()
