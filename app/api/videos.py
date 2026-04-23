from __future__ import annotations

import csv
import io
import shutil
import uuid
import zipfile
from pathlib import Path

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.clients.llm_client import LLMClient
from app.clients.qwen_tts_client import QwenTTSClient
from app.clients.vlm_client import VLMClient
from app.config.config import settings
from app.core.composer import AudioEntry, Composer
from app.core.event_generation import EventService
from app.core.exo_generator import ExoConfig, ExoEntry, ExoGenerator
from app.core.planning import UtterancePlanner
from app.core.progress_store import update_progress
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
from app.models.schemas import TimelineItem, VideoRead, VideoTimeline
from app.utils.logging import logger

router = APIRouter()

# 実況スタイル → TTS instruct テキスト
_STYLE_INSTRUCT: dict[str, str] = {
    "excited": (
        "Speak with high energy and excitement, "
        "like a passionate game streamer at a climactic moment."
    ),
    "neutral": "Speak in a natural, conversational voice like a friendly game commentator.",
    "calm": "Speak slowly and calmly in a relaxed, gentle voice with low energy.",
}


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


@router.get("/", response_model=list[VideoRead])
def list_videos(db: Session = Depends(get_db)) -> list[Video]:
    return db.query(Video).order_by(Video.created_at.desc()).all()


@router.get("/{video_id}", response_model=VideoRead)
def get_video(video_id: str, db: Session = Depends(get_db)) -> Video:
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    return video


@router.get("/{video_id}/timeline", response_model=VideoTimeline)
def get_timeline(video_id: str, db: Session = Depends(get_db)) -> VideoTimeline:
    """動画の発話計画・実況テキスト・音声パスを一覧で返す。"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    storage = Path(video.storage_path)
    media_root = Path(settings.media_root)
    try:
        input_rel = str(storage.relative_to(media_root)).replace("\\", "/")
    except ValueError:
        input_rel = None

    plans = (
        db.query(UtterancePlan)
        .filter(UtterancePlan.video_id == video_id)
        .order_by(UtterancePlan.start_time)
        .all()
    )

    items: list[TimelineItem] = []
    for plan in plans:
        commentary = (
            db.query(Commentary).filter(Commentary.utterance_plan_id == plan.id).first()
        )
        if not commentary:
            continue
        audio = db.query(Audio).filter(Audio.commentary_id == commentary.id).first()
        audio_rel = f"{commentary.id}/audio.wav" if audio and audio.storage_path else None
        items.append(
            TimelineItem(
                start_time=plan.start_time,
                end_time=plan.end_time,
                style=plan.style,
                text=commentary.text,
                commentary_id=str(commentary.id),
                audio_rel=audio_rel,
            )
        )

    return VideoTimeline(input_rel=input_rel, items=items)


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
    vlm_client = VLMClient(
        base_url=settings.llm_api_base,
        api_key=settings.llm_api_key,
        model=settings.vlm_model_name,
    )
    event_service = EventService()
    planner = UtterancePlanner()
    commentary_service = CommentaryService()
    llm_client = LLMClient(
        base_url=settings.llm_api_base,
        api_key=settings.llm_api_key,
        model=settings.llm_model_name,
    )

    update_progress(video_id, "segmentation", 0, "動画を分割中...")
    seg_results = seg_service.execute(video.storage_path, str(video.id))
    logger.info("分割完了: %d セグメント", len(seg_results))
    update_progress(video_id, "segmentation", 10, f"分割完了: {len(seg_results)} セグメント")

    all_events = []
    seg_count = len(seg_results)

    for seg_idx, seg_result in enumerate(seg_results):
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
            analysis = vision_service.analyze_frame(fr.image_path, vlm_client)
            frame = Frame(
                segment_id=segment.id,
                timestamp=fr.timestamp,
                image_path=fr.image_path,
                features=vision_service.to_dict(analysis),
            )
            db.add(frame)
            analyses.append(analysis)

        pct = 10 + int((seg_idx + 1) / seg_count * 60)
        update_progress(video_id, "vision", pct, f"フレーム解析中: {seg_idx + 1}/{seg_count}")

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
    update_progress(video_id, "planning", 75, "発話計画を生成中...")

    plan_results = planner.plan(str(video.id), all_events)
    update_progress(video_id, "planning", 80, f"発話計画完了: {len(plan_results)} 件")
    prev_text = ""
    plan_count = len(plan_results)
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
        pct = 80 + int((plan_idx + 1) / plan_count * 15)
        update_progress(video_id, "commentary", pct, f"実況生成中: {plan_idx + 1}/{plan_count}")
        prev_text = com_data["text"]

    db.commit()
    update_progress(video_id, "done", 100, "処理完了")
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
    plan_count = len(plans)
    update_progress(video_id, "compose", 0, "音声合成を開始...")

    for plan_idx, plan in enumerate(plans):
        commentary = db.query(Commentary).filter(Commentary.utterance_plan_id == plan.id).first()
        if not commentary:
            continue

        pct = int((plan_idx + 1) / plan_count * 80)
        update_progress(video_id, "tts", pct, f"音声合成中: {plan_idx + 1}/{plan_count}")
        audio_path = str(Path(settings.media_root) / str(commentary.id) / "audio.wav")
        instruct = _STYLE_INSTRUCT.get(commentary.style or "", "")
        duration = tts_client.synthesize(commentary.text, audio_path, instruct=instruct)

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

        audio_entries.append(
            AudioEntry(
                audio_path=audio_path,
                start_time=plan.start_time,
                duration_seconds=duration,
            )
        )
        srt_paths.append(srt_result.file_path)

    db.commit()

    update_progress(video_id, "compose", 85, "字幕・動画を合成中...")
    # 全字幕を結合した SRT ファイルを生成
    merged_srt = _merge_srt(srt_paths, video_id, settings.media_root)
    output_path = str(Path(settings.media_root) / str(video_id) / "output.mp4")
    composer.compose(video.storage_path, audio_entries, merged_srt, output_path)

    logger.info("合成完了: %s", output_path)
    update_progress(video_id, "done", 100, "合成完了")
    return {"status": "ok", "output_path": output_path}


@router.get("/{video_id}/export")
def export_video(video_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    """生成済みの実況データを ZIP でエクスポートする。

    ZIP 構成:
      input/{filename}     — 元動画ファイル
      audio/               — 各発話の WAV ファイル（{commentary_id}.wav）
      subtitles/           — 各発話の SRT ファイル
      commentary.csv       — 発話一覧（start_time, end_time, text, style, audio_file, srt_file）
      timeline.exo         — AviUtl 拡張編集タイムライン（元動画参照）
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    plans = (
        db.query(UtterancePlan)
        .filter(UtterancePlan.video_id == video_id)
        .order_by(UtterancePlan.start_time)
        .all()
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 元動画を input/ に追加
        input_path = Path(video.storage_path)
        input_arcname = f"input/{input_path.name}"
        if input_path.exists():
            zf.write(str(input_path), input_arcname)

        csv_rows: list[dict] = []

        for plan in plans:
            commentary = (
                db.query(Commentary).filter(Commentary.utterance_plan_id == plan.id).first()
            )
            if not commentary:
                continue

            audio = db.query(Audio).filter(Audio.commentary_id == commentary.id).first()
            subtitle = db.query(Subtitle).filter(Subtitle.commentary_id == commentary.id).first()

            audio_arcname = ""
            srt_arcname = ""

            if audio and audio.storage_path and Path(audio.storage_path).exists():
                audio_arcname = f"audio/{commentary.id}.wav"
                zf.write(audio.storage_path, audio_arcname)

            if subtitle and subtitle.file_path and Path(subtitle.file_path).exists():
                srt_arcname = f"subtitles/{commentary.id}.srt"
                zf.write(subtitle.file_path, srt_arcname)

            csv_rows.append(
                {
                    "start_time": plan.start_time,
                    "end_time": plan.end_time,
                    "text": commentary.text,
                    "style": commentary.style,
                    "audio_file": audio_arcname,
                    "srt_file": srt_arcname,
                }
            )

        # commentary.csv を生成して ZIP に追加
        csv_buf = io.StringIO()
        writer = csv.DictWriter(
            csv_buf,
            fieldnames=["start_time", "end_time", "text", "style", "audio_file", "srt_file"],
        )
        writer.writeheader()
        writer.writerows(csv_rows)
        zf.writestr("commentary.csv", csv_buf.getvalue())

        # timeline.exo を生成して ZIP に追加（元動画を参照）
        exo_entries = [
            ExoEntry(
                audio_file=row["audio_file"].replace("/", "\\"),
                start_time=float(row["start_time"]),
                duration_seconds=float(row["end_time"]) - float(row["start_time"]),
                text=row["text"],
            )
            for row in csv_rows
            if row["audio_file"]
        ]
        exo_config = ExoConfig(
            fps=video.fps or 30.0,
            total_duration=video.duration_seconds or 0.0,
        )
        exo_bytes = ExoGenerator().generate(
            input_arcname.replace("/", "\\"), exo_entries, exo_config
        )
        zf.writestr("timeline.exo", exo_bytes)

    buf.seek(0)
    filename = f"aituber_export_{video_id[:8]}.zip"
    logger.info("エクスポート: %s (%d 発話)", filename, len(csv_rows))
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
