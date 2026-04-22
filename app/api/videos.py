from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
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
from app.db.session import get_db
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
from app.models.schemas import VideoRead
from app.utils.logging import logger

router = APIRouter()


@router.post("/", response_model=VideoRead, status_code=201)
def upload_video(
    title: str = Query(default=""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Video:
    """動画ファイルをアップロードして DB に登録する。"""
    video_id = uuid.uuid4()
    media_dir = Path(settings.media_root) / str(video_id)
    media_dir.mkdir(parents=True, exist_ok=True)

    dest_path = media_dir / (file.filename or "input.mp4")
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    duration, fps = _probe_video_meta(str(dest_path))

    video = Video(
        id=video_id,
        title=title or (file.filename or "untitled"),
        duration_seconds=duration,
        fps=fps,
        storage_path=str(dest_path),
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    logger.info("動画登録: video_id=%s", video_id)
    return video


@router.get("/{video_id}", response_model=VideoRead)
def get_video(video_id: str, db: Session = Depends(get_db)) -> Video:
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    return video


@router.post("/{video_id}/process")
def process_video(video_id: str, db: Session = Depends(get_db)) -> dict:
    """動画を分割 → フレーム抽出 → イベント検出 → 発話計画 → 実況生成まで実行する。"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    seg_service = SegmentationService(
        segment_duration=settings.segment_duration,
        media_root=settings.media_root,
    )
    frame_extractor = FrameExtractor(media_root=settings.media_root)
    vision_service = VisionService()
    event_service = EventService()
    planner = UtterancePlanner()
    commentary_service = CommentaryService()
    llm_client = LLMClient(
        base_url=settings.llm_api_base,
        api_key=settings.llm_api_key,
        model=settings.llm_model_name,
    )

    seg_results = seg_service.execute(video.storage_path, str(video.id))
    logger.info("分割完了: %d セグメント", len(seg_results))

    all_events = []

    for seg_result in seg_results:
        segment = Segment(
            video_id=video.id,
            start_time=seg_result.start_time,
            end_time=seg_result.end_time,
            segment_type=seg_result.segment_type,
            storage_path=seg_result.storage_path,
        )
        db.add(segment)
        db.flush()

        frame_results = frame_extractor.extract(
            video.storage_path,
            str(segment.id),
            seg_result.start_time,
            seg_result.end_time,
        )

        analyses = []
        for fr in frame_results:
            analysis = vision_service.analyze_frame(fr.image_path)
            frame = Frame(
                segment_id=segment.id,
                timestamp=fr.timestamp,
                image_path=fr.image_path,
                features=vision_service.to_dict(analysis),
            )
            db.add(frame)
            analyses.append(analysis)

        event_results = event_service.generate(str(segment.id), seg_result.start_time, analyses)
        for er in event_results:
            event = Event(
                segment_id=segment.id,
                timestamp=er.timestamp,
                event_type=er.event_type,
                importance=er.importance,
                details=er.details,
            )
            db.add(event)
            all_events.append(er)

    db.commit()

    plan_results = planner.plan(str(video.id), all_events)
    prev_text = ""
    for pr in plan_results:
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

        relevant_events = [e for e in all_events if e.event_id in pr.event_ids]
        com_data = commentary_service.generate(pr, relevant_events, llm_client, prev_text)
        commentary = Commentary(
            utterance_plan_id=plan.id,
            language=com_data["language"],
            style=com_data["style"],
            text=com_data["text"],
            llm_raw_response=com_data["llm_raw_response"],
        )
        db.add(commentary)
        prev_text = com_data["text"]

    db.commit()
    return {"status": "ok", "video_id": video_id, "plans": len(plan_results)}


@router.post("/{video_id}/compose")
def compose_video(video_id: str, db: Session = Depends(get_db)) -> dict:
    """実況音声・字幕を合成して最終動画を出力する。"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    tts_client = QwenTTSClient(
        base_url=settings.tts_base_url,
        default_mode=settings.tts_default_mode,
        default_speaker=settings.tts_default_speaker,
        default_language=settings.tts_default_language,
        default_instruct=settings.tts_default_instruct,
    )
    subtitle_service = SubtitleService()
    composer = Composer(media_root=settings.media_root)

    plans = (
        db.query(UtterancePlan)
        .filter(UtterancePlan.video_id == video_id)
        .order_by(UtterancePlan.start_time)
        .all()
    )

    audio_entries = []
    srt_paths = []

    for plan in plans:
        commentary = (
            db.query(Commentary)
            .filter(Commentary.utterance_plan_id == plan.id)
            .first()
        )
        if not commentary:
            continue

        audio_path = str(Path(settings.media_root) / str(commentary.id) / "audio.wav")
        duration = tts_client.synthesize(commentary.text, audio_path)

        audio = Audio(
            commentary_id=commentary.id,
            storage_path=audio_path,
            duration_seconds=duration,
        )
        db.add(audio)

        srt_result = subtitle_service.generate(
            commentary.text,
            plan.start_time,
            duration,
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

        audio_entries.append(AudioEntry(
            audio_path=audio_path,
            start_time=plan.start_time,
            duration_seconds=duration,
        ))
        srt_paths.append(srt_result.file_path)

    db.commit()

    # 全字幕を結合した SRT ファイルを生成
    merged_srt = _merge_srt(srt_paths, video_id, settings.media_root)
    output_path = str(Path(settings.media_root) / str(video_id) / "output.mp4")
    composer.compose(video.storage_path, audio_entries, merged_srt, output_path)

    logger.info("合成完了: %s", output_path)
    return {"status": "ok", "output_path": output_path}


def _probe_video_meta(video_path: str) -> tuple[float, float]:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    duration = frame_count / fps if fps > 0 else 0.0
    return duration, fps


def _merge_srt(srt_paths: list[str], video_id: str, media_root: str) -> str | None:
    valid = [p for p in srt_paths if Path(p).exists()]
    if not valid:
        return None
    merged_path = Path(media_root) / video_id / "merged.srt"
    with open(merged_path, "w", encoding="utf-8") as out:
        for path in valid:
            out.write(Path(path).read_text(encoding="utf-8"))
    return str(merged_path)
