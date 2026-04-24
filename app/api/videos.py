from __future__ import annotations

import csv
import io
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path
from typing import Any

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.clients.llm_client import LLMClient
from app.clients.qwen_tts_client import QwenTTSClient
from app.clients.vlm_client import VLMClient
from app.config.config import get_runtime_settings, settings
from app.core.composer import AudioEntry, Composer
from app.core.event_generation import EventService
from app.core.exo_generator import ExoConfig, ExoEntry, ExoGenerator
from app.core.planning import UtterancePlanner
from app.core.progress_store import update_progress
from app.core.prompt import CommentaryService
from app.core.rule_tagger import RuleTagger
from app.core.segmentation import FrameExtractor, SegmentationService
from app.core.subtitle import SubtitleService
from app.core.tags import (
    build_tag_source_map,
    mark_llm_tag_status_skipped,
    normalize_video_metadata,
)
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
from app.models.schemas import TimelineItem, VideoRead, VideoTagRead, VideoTimeline, VideoUpdate
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
) -> VideoRead:
    """動画ファイルをアップロードして DB に登録する。"""
    video_id = uuid.uuid4()
    media_dir = Path(settings.media_root) / str(video_id)
    media_dir.mkdir(parents=True, exist_ok=True)

    dest_path = media_dir / (file.filename or "input.mp4")
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        duration, fps = _probe_video_meta(str(dest_path))
    except Exception as e:
        logger.error("動画メタ情報取得失敗: %s", e)
        shutil.rmtree(media_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

    try:
        _generate_thumbnail(str(dest_path), str(media_dir / "thumbnail.jpg"))
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        logger.error("サムネイル生成失敗: %s", stderr)
    except Exception as e:
        logger.error("サムネイル生成失敗: %s", e)

    video = Video(
        id=video_id,
        title=title or (file.filename or "untitled"),
        duration_seconds=duration,
        fps=fps,
        storage_path=str(dest_path),
        video_metadata=normalize_video_metadata(None),
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    logger.info("動画登録: video_id=%s", video_id)
    return _to_video_read(video)


@router.get("/", response_model=list[VideoRead])
def list_videos(db: Session = Depends(get_db)) -> list[VideoRead]:
    videos = db.query(Video).order_by(Video.created_at.desc()).all()
    return [_to_video_read(video) for video in videos]


@router.delete("/{video_id}")
def delete_video(video_id: str, db: Session = Depends(get_db)) -> dict:
    """動画レコードと関連メディアを削除する。"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    media_dir = Path(settings.media_root) / str(video.id)
    try:
        if media_dir.exists():
            shutil.rmtree(media_dir)
    except Exception as e:
        logger.error("動画ディレクトリ削除失敗: %s", e)
        raise HTTPException(status_code=500, detail="メディア削除に失敗しました") from e

    try:
        db.delete(video)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("動画レコード削除失敗: %s", e)
        raise HTTPException(status_code=500, detail="動画削除に失敗しました") from e

    logger.info("動画削除: video_id=%s", video_id)
    return {"status": "ok", "video_id": video_id}


@router.get("/{video_id}", response_model=VideoRead)
def get_video(video_id: str, db: Session = Depends(get_db)) -> VideoRead:
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    return _to_video_read(video)


@router.get("/{video_id}/tags", response_model=VideoTagRead)
def get_video_tags(video_id: str, db: Session = Depends(get_db)) -> VideoTagRead:
    """動画タグ（manual/rule/llm/effective）とソース情報を返す。"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    return _to_video_tag_read(video.video_metadata)


@router.patch("/{video_id}", response_model=VideoRead)
def update_video(video_id: str, payload: VideoUpdate, db: Session = Depends(get_db)) -> VideoRead:
    """動画のタイトル・タグを更新する。"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    if payload.title is not None:
        new_title = payload.title.strip()
        if not new_title:
            raise HTTPException(status_code=400, detail="タイトルが空です")
        video.title = new_title

    manual_tags = payload.tags_manual if payload.tags_manual is not None else payload.tags
    if manual_tags is not None:
        metadata = normalize_video_metadata(video.video_metadata)
        metadata["tags_manual"] = _normalize_tags(manual_tags)
        video.video_metadata = normalize_video_metadata(metadata)

    try:
        db.add(video)
        db.commit()
        db.refresh(video)
    except Exception as e:
        db.rollback()
        logger.error("動画更新失敗: %s", e)
        raise HTTPException(status_code=500, detail="動画更新に失敗しました") from e

    return _to_video_read(video)


@router.post("/{video_id}/tags/rule:refresh", response_model=VideoTagRead)
def refresh_video_rule_tags(video_id: str, db: Session = Depends(get_db)) -> VideoTagRead:
    """RuleTagger で tags_auto_rule を再生成する。"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    cfg = get_runtime_settings(db)
    metadata = _refresh_rule_tags(video, cfg)
    video.video_metadata = metadata

    try:
        db.add(video)
        db.commit()
        db.refresh(video)
    except Exception as e:
        db.rollback()
        logger.error("rule タグ再生成失敗: %s", e)
        raise HTTPException(status_code=500, detail="rule タグ再生成に失敗しました") from e

    return _to_video_tag_read(video.video_metadata)


@router.post("/{video_id}/tags/llm:refresh", response_model=VideoTagRead)
def refresh_video_llm_tags(video_id: str, db: Session = Depends(get_db)) -> VideoTagRead:
    """LLM タグ再生成を実行する（現状は未実装のためスキップ）。"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    metadata = _refresh_llm_tags(video.video_metadata)
    video.video_metadata = metadata

    try:
        db.add(video)
        db.commit()
        db.refresh(video)
    except Exception as e:
        db.rollback()
        logger.error("llm タグ再生成失敗: %s", e)
        raise HTTPException(status_code=500, detail="llm タグ再生成に失敗しました") from e

    return _to_video_tag_read(video.video_metadata)


@router.post("/{video_id}/tags/refresh", response_model=VideoTagRead)
def refresh_video_tags(video_id: str, db: Session = Depends(get_db)) -> VideoTagRead:
    """Rule/LLM のタグ再生成をまとめて実行する。"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    cfg = get_runtime_settings(db)
    metadata = _refresh_rule_tags(video, cfg)
    metadata = _refresh_llm_tags(metadata)
    video.video_metadata = metadata

    try:
        db.add(video)
        db.commit()
        db.refresh(video)
    except Exception as e:
        db.rollback()
        logger.error("タグ再生成失敗: %s", e)
        raise HTTPException(status_code=500, detail="タグ再生成に失敗しました") from e

    return _to_video_tag_read(video.video_metadata)


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
        commentary = db.query(Commentary).filter(Commentary.utterance_plan_id == plan.id).first()
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

    cfg = get_runtime_settings(db)
    video.video_metadata = _refresh_rule_tags(video, cfg)
    db.add(video)
    db.commit()

    seg_service = SegmentationService(
        segment_duration=cfg.segment_duration,
        media_root=cfg.media_root,
    )
    frame_extractor = FrameExtractor(media_root=cfg.media_root)
    vision_service = VisionService()
    vlm_client = VLMClient(
        base_url=cfg.llm_api_base,
        api_key=cfg.llm_api_key,
        model=cfg.vlm_model_name,
    )
    event_service = EventService()
    planner = UtterancePlanner(
        min_silence_seconds=cfg.planner_min_silence_seconds,
        plan_duration=cfg.planner_plan_duration_seconds,
        speak_threshold=cfg.planner_speak_threshold,
        max_talk_ratio=cfg.planner_max_talk_ratio,
        talk_window_seconds=cfg.planner_talk_window_seconds,
        max_queue_delay_seconds=cfg.planner_max_queue_delay_seconds,
    )
    commentary_service = CommentaryService()
    llm_client = LLMClient(
        base_url=cfg.llm_api_base,
        api_key=cfg.llm_api_key,
        model=cfg.llm_model_name,
    )

    update_progress(video_id, "segmentation", 0, "動画を分割中...")
    try:
        seg_results = seg_service.execute(video.storage_path, str(video.id))
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        logger.error("FFmpeg 分割失敗: %s", stderr)
        raise HTTPException(status_code=500, detail=f"FFmpeg エラー: {stderr[:500]}") from e
    except Exception as e:
        logger.error("process エラー: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
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

    cfg = get_runtime_settings(db)

    tts_client = QwenTTSClient(
        base_url=cfg.tts_base_url,
        default_mode=cfg.tts_default_mode,
        default_speaker=cfg.tts_default_speaker,
        default_language=cfg.tts_default_language,
        default_instruct=cfg.tts_default_instruct,
    )
    subtitle_service = SubtitleService()
    composer = Composer(media_root=cfg.media_root, game_audio_volume=cfg.game_audio_volume)

    plans = (
        db.query(UtterancePlan)
        .filter(UtterancePlan.video_id == video_id)
        .order_by(UtterancePlan.start_time)
        .all()
    )

    pending_entries: list[tuple[UtterancePlan, Commentary, AudioEntry]] = []
    audio_entries: list[AudioEntry] = []
    srt_paths: list[str] = []
    plan_count = len(plans)
    update_progress(video_id, "compose", 0, "音声合成を開始...")

    try:
        for plan_idx, plan in enumerate(plans):
            commentary = (
                db.query(Commentary).filter(Commentary.utterance_plan_id == plan.id).first()
            )
            if not commentary:
                continue

            pct = int((plan_idx + 1) / plan_count * 80)
            update_progress(video_id, "tts", pct, f"音声合成中: {plan_idx + 1}/{plan_count}")
            audio_path = str(Path(cfg.media_root) / str(commentary.id) / "audio.wav")
            instruct = _STYLE_INSTRUCT.get(commentary.style or "", "")
            duration = tts_client.synthesize(commentary.text, audio_path, instruct=instruct)

            audio = Audio(
                commentary_id=commentary.id,
                storage_path=audio_path,
                duration_seconds=duration,
            )
            db.add(audio)

            pending_entries.append(
                (
                    plan,
                    commentary,
                    AudioEntry(
                        audio_path=audio_path,
                        start_time=plan.start_time,
                        duration_seconds=duration,
                    ),
                )
            )

        normalized_entries = composer.schedule_entries(
            [entry for _, _, entry in pending_entries],
            min_gap_seconds=cfg.compose_overlap_min_gap_seconds,
        )

        for index, (plan, commentary, _) in enumerate(pending_entries):
            normalized = normalized_entries[index]
            if abs(normalized.start_time - plan.start_time) > 1e-6:
                logger.info(
                    "発話開始時刻を調整: plan_id=%s old=%.3f new=%.3f",
                    plan.id,
                    plan.start_time,
                    normalized.start_time,
                )

            plan.start_time = normalized.start_time
            plan.end_time = normalized.start_time + normalized.duration_seconds

            srt_result = subtitle_service.generate(
                commentary.text,
                normalized.start_time,
                normalized.duration_seconds,
                str(commentary.id),
                cfg.media_root,
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
                    audio_path=normalized.audio_path,
                    start_time=normalized.start_time,
                    duration_seconds=normalized.duration_seconds,
                )
            )
            srt_paths.append(srt_result.file_path)

        db.commit()

        update_progress(video_id, "compose", 85, "字幕・動画を合成準備中...")
        update_progress(video_id, "compose", 88, "字幕ファイルを結合中...")
        merged_srt = _merge_srt(srt_paths, video_id, cfg.media_root)
        update_progress(video_id, "compose", 92, "映像・音声を合成中（FFmpeg）...")
        output_path = str(Path(cfg.media_root) / str(video_id) / "output.mp4")
        composer.compose(video.storage_path, audio_entries, merged_srt, output_path)
        update_progress(video_id, "compose", 98, "最終処理中...")

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        logger.error("FFmpeg 合成失敗: %s", stderr)
        raise HTTPException(status_code=500, detail=f"FFmpeg エラー: {stderr[:500]}") from e
    except Exception as e:
        logger.error("合成エラー: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

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


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        tag = raw.strip()
        if not tag:
            continue
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(tag)
    return normalized


def _generate_thumbnail(video_path: str, thumbnail_path: str) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-ss",
            "00:00:01",
            "-frames:v",
            "1",
            thumbnail_path,
        ],
        check=True,
        capture_output=True,
    )


def _to_video_read(video: Video) -> VideoRead:
    """動画レスポンス用にタグメタデータを正規化する。"""
    metadata = normalize_video_metadata(video.video_metadata)
    return VideoRead(
        id=video.id,
        title=video.title,
        duration_seconds=video.duration_seconds,
        fps=video.fps,
        storage_path=video.storage_path,
        video_metadata=metadata,
        created_at=video.created_at,
    )


def _refresh_rule_tags(video: Video, cfg: Any) -> dict[str, Any]:
    """RuleTagger で自動タグを更新する。"""
    rule_tagger = RuleTagger()
    metadata = normalize_video_metadata(video.video_metadata)
    metadata["tags_auto_rule"] = rule_tagger.generate(
        tts_mode=cfg.tts_default_mode,
        llm_model=cfg.llm_model_name,
        vlm_model=cfg.vlm_model_name,
        duration_seconds=video.duration_seconds,
        fps=video.fps,
    )
    tag_status = dict(metadata.get("tag_status", {}))
    tag_status["rule"] = "ready"
    metadata["tag_status"] = tag_status
    return normalize_video_metadata(metadata)


def _refresh_llm_tags(raw_metadata: dict[str, Any] | None) -> dict[str, Any]:
    """LLM タグ更新をスキップし、状態のみ更新する。"""
    return mark_llm_tag_status_skipped(raw_metadata)


def _to_video_tag_read(raw_metadata: dict[str, Any] | None) -> VideoTagRead:
    """タグ情報の API レスポンスを構築する。"""
    metadata = normalize_video_metadata(raw_metadata)
    source_map = build_tag_source_map(metadata)
    return VideoTagRead(
        tags_manual=metadata["tags_manual"],
        tags_auto_rule=metadata["tags_auto_rule"],
        tags_auto_llm=metadata["tags_auto_llm"],
        tags_suggested_llm=metadata["tags_suggested_llm"],
        tags_effective=metadata["tags_effective"],
        source_by_tag=source_map,
        tag_status=metadata["tag_status"],
    )
