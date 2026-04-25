"""動画管理・パイプライン実行関連の API エンドポイントを提供する。"""

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
from app.core.event_generation import EventResult, EventService
from app.core.exo_generator import ExoConfig, ExoEntry, ExoGenerator
from app.core.planning import UtterancePlanner
from app.core.progress_store import update_progress
from app.core.prompt import CommentaryService
from app.core.rule_tagger import RuleTagger
from app.core.segmentation import FrameExtractor, SegmentationService
from app.core.subtitle import SubtitleService
from app.core.tags import (
    build_tag_source_map,
    normalize_video_metadata,
)
from app.core.video_tagging import refresh_llm_tags
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
from app.utils.pipeline_debug import PipelineDebugRecorder
from app.utils.pipeline_performance import PipelinePerformanceRecorder
from app.utils.pipeline_state import PipelineSegmentStateStore

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
    """動画ファイルをアップロードして DB に登録する。

    Args:
        title: 明示指定された動画タイトル。空文字の場合はファイル名を代替で使用する。
        file: クライアントから受け取る動画ファイル本体。
        db: 動画レコードの保存に使う DB セッション。

    Returns:
        登録した動画のメタ情報を含むレスポンス。
    """
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
    """登録済み動画一覧を作成日時の降順で返す。

    Args:
        db: 動画一覧を取得する DB セッション。

    Returns:
        新しい順に並んだ動画一覧。
    """
    videos = db.query(Video).order_by(Video.created_at.desc()).all()
    return [_to_video_read(video) for video in videos]


@router.delete("/{video_id}")
def delete_video(video_id: str, db: Session = Depends(get_db)) -> dict:
    """動画レコードと関連メディアを削除する。

    Args:
        video_id: 削除対象動画の ID。
        db: レコード削除に使用する DB セッション。

    Returns:
        削除結果 (`status`, `video_id`) を含む辞書。
    """
    video = _get_video_or_404(db, video_id)

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
    """動画IDを指定して動画詳細を返す。

    Args:
        video_id: 取得対象動画の ID。
        db: 動画情報を取得する DB セッション。

    Returns:
        対象動画の詳細情報。
    """
    video = _get_video_or_404(db, video_id)
    return _to_video_read(video)


@router.get("/{video_id}/tags", response_model=VideoTagRead)
def get_video_tags(video_id: str, db: Session = Depends(get_db)) -> VideoTagRead:
    """動画タグ（manual/rule/llm/effective）とソース情報を返す。

    Args:
        video_id: タグを取得する動画の ID。
        db: 動画レコード参照に使う DB セッション。

    Returns:
        手動タグ・自動タグ・有効タグとタグソースをまとめたレスポンス。
    """
    video = _get_video_or_404(db, video_id)
    return _to_video_tag_read(video.video_metadata)


@router.patch("/{video_id}", response_model=VideoRead)
def update_video(video_id: str, payload: VideoUpdate, db: Session = Depends(get_db)) -> VideoRead:
    """動画のタイトル・タグを更新する。

    Args:
        video_id: 更新対象動画の ID。
        payload: 更新内容。タイトルと手動タグの更新を受け付ける。
        db: 更新処理に利用する DB セッション。

    Returns:
        更新後の動画情報。
    """
    video = _get_video_or_404(db, video_id)

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
    """RuleTagger で tags_auto_rule を再生成する。

    Args:
        video_id: ルールベースタグを更新する動画の ID。
        db: 動画取得・保存に利用する DB セッション。

    Returns:
        更新後タグ情報。
    """
    video = _get_video_or_404(db, video_id)

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
    """LLM タグを再生成する。

    Args:
        video_id: LLM タグを更新する動画の ID。
        db: 動画取得・保存に利用する DB セッション。

    Returns:
        更新後タグ情報。
    """
    video = _get_video_or_404(db, video_id)

    cfg = get_runtime_settings(db)
    llm_client = LLMClient(
        base_url=cfg.llm_api_base,
        api_key=cfg.llm_api_key,
        model=cfg.llm_model_name,
    )
    metadata = refresh_llm_tags(
        video_id=str(video.id),
        video_title=video.title,
        raw_metadata=video.video_metadata,
        llm_client=llm_client,
    )
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
    """Rule/LLM のタグ再生成をまとめて実行する。

    Args:
        video_id: タグ再生成対象動画の ID。
        db: タグ更新結果を保存する DB セッション。

    Returns:
        ルール・LLM 両方の更新を反映したタグ情報。
    """
    video = _get_video_or_404(db, video_id)

    cfg = get_runtime_settings(db)
    llm_client = LLMClient(
        base_url=cfg.llm_api_base,
        api_key=cfg.llm_api_key,
        model=cfg.llm_model_name,
    )
    metadata = _refresh_rule_tags(video, cfg)
    metadata = refresh_llm_tags(
        video_id=str(video.id),
        video_title=video.title,
        raw_metadata=metadata,
        llm_client=llm_client,
    )
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
    """動画の発話計画・実況テキスト・音声パスを一覧で返す。

    Args:
        video_id: タイムラインを取得する動画の ID。
        db: 発話計画と実況データを参照する DB セッション。

    Returns:
        入力動画相対パスと実況タイムライン項目の集合。
    """
    video = _get_video_or_404(db, video_id)

    storage = Path(video.storage_path)
    media_root = Path(settings.media_root)
    try:
        input_rel = str(storage.relative_to(media_root)).replace("\\", "/")
    except ValueError:
        input_rel = None

    plans = (
        db.query(UtterancePlan)
        .filter(UtterancePlan.video_id == video.id)
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
def process_video(
    video_id: str,
    rerun_failed_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> dict:
    """動画を分割 → フレーム抽出 → イベント検出 → 発話計画 → 実況生成まで実行する。

    Args:
        video_id: 処理対象動画の ID。
        rerun_failed_only: `True` の場合は前回失敗したセグメントのみ再処理する。
        db: 各ステップ結果を読み書きする DB セッション。

    Returns:
        実行結果サマリー。処理済み/再利用/失敗セグメント番号を含む。
    """
    video = _get_video_or_404(db, video_id)
    current_video_id = str(video.id)

    cfg = get_runtime_settings(db)
    debug_recorder = PipelineDebugRecorder(cfg.media_root, str(video.id))
    perf_recorder = PipelinePerformanceRecorder(cfg.media_root, str(video.id))
    perf_recorder.checkpoint(
        "process_started",
        payload={"video_id": current_video_id, "rerun_failed_only": rerun_failed_only},
    )
    state_store = PipelineSegmentStateStore(cfg.media_root, str(video.id))
    llm_client = LLMClient(
        base_url=cfg.llm_api_base,
        api_key=cfg.llm_api_key,
        model=cfg.llm_model_name,
    )
    original_metadata = video.video_metadata
    metadata = _refresh_rule_tags(video, cfg)
    metadata = refresh_llm_tags(
        video_id=str(video.id),
        video_title=video.title,
        raw_metadata=metadata,
        llm_client=llm_client,
    )
    video.video_metadata = metadata
    db.add(video)
    db.commit()
    debug_recorder.save_step_io(
        "tag_refresh",
        input_data={
            "video_id": str(video.id),
            "title": video.title,
            "video_metadata": original_metadata,
        },
        output_data={"video_metadata": metadata},
    )
    perf_recorder.checkpoint(
        "tag_refresh_done",
        payload={"tag_status": metadata.get("tag_status", {})},
    )

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
    update_progress(current_video_id, "segmentation", 0, "動画を分割中...")
    try:
        seg_results = seg_service.execute(video.storage_path, str(video.id))
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        logger.error("FFmpeg 分割失敗: %s", stderr)
        perf_recorder.finalize(
            {"status": "error", "stage": "segmentation", "error": f"ffmpeg: {stderr[:200]}"}
        )
        raise HTTPException(status_code=500, detail=f"FFmpeg エラー: {stderr[:500]}") from e
    except Exception as e:
        logger.error("process エラー: %s", e)
        perf_recorder.finalize({"status": "error", "stage": "segmentation", "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e)) from e

    state_store.sync_segments(seg_results)
    failed_target_indexes = set(state_store.failed_indexes()) if rerun_failed_only else set()

    logger.info(
        "分割完了: %d セグメント rerun_failed_only=%s targets=%s",
        len(seg_results),
        rerun_failed_only,
        sorted(failed_target_indexes),
    )
    debug_recorder.save_step_io(
        "segmentation",
        input_data={
            "video_id": str(video.id),
            "storage_path": video.storage_path,
            "segment_duration": cfg.segment_duration,
            "rerun_failed_only": rerun_failed_only,
            "failed_target_indexes": sorted(failed_target_indexes),
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
    perf_recorder.checkpoint(
        "segmentation_done",
        payload={"segment_count": len(seg_results)},
    )
    update_progress(
        current_video_id, "segmentation", 10, f"分割完了: {len(seg_results)} セグメント"
    )

    if not rerun_failed_only:
        removed_segments = (
            db.query(Segment).filter(Segment.video_id == video.id).delete(synchronize_session=False)
        )
        removed_plans = (
            db.query(UtterancePlan)
            .filter(UtterancePlan.video_id == video.id)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(
            "既存処理結果を初期化: video_id=%s removed_segments=%d removed_plans=%d",
            current_video_id,
            removed_segments,
            removed_plans,
        )

    all_events: list[EventResult] = []
    segment_debug_summaries: list[dict[str, Any]] = []
    failed_segment_indexes: list[int] = []
    processed_segment_indexes: list[int] = []
    reused_segment_indexes: list[int] = []
    seg_count = len(seg_results)

    for seg_idx, seg_result in enumerate(seg_results):
        logger.debug(
            "segment処理開始: video_id=%s index=%d/%d range=%.2f-%.2f",
            current_video_id,
            seg_idx + 1,
            seg_count,
            seg_result.start_time,
            seg_result.end_time,
        )
        existing_segment = _find_segment_by_time(
            db,
            video_id=video.id,
            start_time=seg_result.start_time,
            end_time=seg_result.end_time,
        )
        should_reprocess = (not rerun_failed_only) or (seg_idx in failed_target_indexes)

        if rerun_failed_only and not should_reprocess and existing_segment is not None:
            existing_event_results = _events_to_results(
                existing_segment.events,
                speak_threshold=planner.speak_threshold,
            )
            all_events.extend(existing_event_results)
            reused_segment_indexes.append(seg_idx)
            state_store.mark_completed(
                seg_idx,
                segment_id=str(existing_segment.id),
                frame_count=len(existing_segment.frames),
                event_count=len(existing_segment.events),
            )
            debug_recorder.append_segment_debug(
                segment_index=seg_idx,
                segment_id=str(existing_segment.id),
                stage="reuse_existing",
                input_data={
                    "start_time": seg_result.start_time,
                    "end_time": seg_result.end_time,
                },
                output_data={
                    "frame_count": len(existing_segment.frames),
                    "event_count": len(existing_segment.events),
                },
            )
            segment_debug_summaries.append(
                {
                    "segment_index": seg_idx,
                    "segment_id": str(existing_segment.id),
                    "start_time": seg_result.start_time,
                    "end_time": seg_result.end_time,
                    "frame_count": len(existing_segment.frames),
                    "analysis_count": len(existing_segment.frames),
                    "event_count": len(existing_segment.events),
                    "reused": True,
                }
            )
            continue

        if rerun_failed_only and not should_reprocess and existing_segment is None:
            logger.info(
                "再利用対象セグメントの既存データがないため再処理へ切替: video_id=%s index=%d",
                current_video_id,
                seg_idx,
            )

        try:
            with db.begin_nested():
                if existing_segment is not None:
                    db.delete(existing_segment)
                    db.flush()

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
                    video.storage_path,
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
                        "video_path": video.storage_path,
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
                    analysis = vision_service.analyze_frame(fr.image_path, vlm_client)
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

                pct = 10 + int((seg_idx + 1) / seg_count * 60)
                update_progress(
                    current_video_id,
                    "vision",
                    pct,
                    f"フレーム解析中: {seg_idx + 1}/{seg_count}",
                )

                event_results = event_service.generate(
                    str(segment.id), seg_result.start_time, analyses
                )
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

            all_events.extend(event_results)
            processed_segment_indexes.append(seg_idx)
            state_store.mark_completed(
                seg_idx,
                segment_id=str(segment.id),
                frame_count=len(frame_results),
                event_count=len(event_results),
            )
            segment_debug_summaries.append(
                {
                    "segment_index": seg_idx,
                    "segment_id": str(segment.id),
                    "start_time": seg_result.start_time,
                    "end_time": seg_result.end_time,
                    "frame_count": len(frame_results),
                    "analysis_count": len(analysis_debug_rows),
                    "event_count": len(event_results),
                    "reused": False,
                }
            )
            logger.debug(
                "segment処理完了: video_id=%s segment_id=%s frames=%d events=%d",
                current_video_id,
                segment.id,
                len(frame_results),
                len(event_results),
            )
        except Exception as e:
            logger.error(
                "segment処理失敗: video_id=%s index=%d error=%s",
                current_video_id,
                seg_idx,
                e,
            )
            state_store.mark_failed(seg_idx, str(e))
            failed_segment_indexes.append(seg_idx)
            debug_recorder.append_segment_debug(
                segment_index=seg_idx,
                segment_id=str(existing_segment.id) if existing_segment is not None else "",
                stage="segment_failed",
                input_data={
                    "start_time": seg_result.start_time,
                    "end_time": seg_result.end_time,
                },
                output_data={"error": str(e)},
            )

    db.commit()

    # 発話計画と実況は最新イベントから必ず再生成する。
    removed_plans_for_rebuild = (
        db.query(UtterancePlan)
        .filter(UtterancePlan.video_id == video.id)
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info(
        "発話計画再生成のため既存 plan を削除: video_id=%s removed_plans=%d",
        current_video_id,
        removed_plans_for_rebuild,
    )

    if failed_segment_indexes:
        logger.warning(
            "segment処理で失敗を検知: video_id=%s failed_indexes=%s",
            current_video_id,
            sorted(failed_segment_indexes),
        )

    debug_recorder.save_step_io(
        "segment_pipeline",
        input_data={
            "segment_count": seg_count,
            "rerun_failed_only": rerun_failed_only,
        },
        output_data={
            "processed_indexes": sorted(processed_segment_indexes),
            "reused_indexes": sorted(reused_segment_indexes),
            "failed_indexes": sorted(failed_segment_indexes),
            "total_event_count": len(all_events),
            "segments": segment_debug_summaries,
        },
    )
    perf_recorder.checkpoint(
        "segment_pipeline_done",
        payload={
            "processed_count": len(processed_segment_indexes),
            "reused_count": len(reused_segment_indexes),
            "failed_count": len(failed_segment_indexes),
            "event_count": len(all_events),
        },
    )
    update_progress(current_video_id, "planning", 75, "発話計画を生成中...")

    plan_results = planner.plan(str(video.id), all_events)
    debug_recorder.save_step_io(
        "planning",
        input_data={"event_count": len(all_events)},
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
    perf_recorder.checkpoint(
        "planning_done",
        payload={"plan_count": len(plan_results)},
    )
    update_progress(current_video_id, "planning", 80, f"発話計画完了: {len(plan_results)} 件")
    prev_text = ""
    plan_count = len(plan_results)
    commentary_debug_rows: list[dict[str, Any]] = []
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
        if plan_count > 0:
            pct = 80 + int((plan_idx + 1) / plan_count * 15)
            update_progress(
                current_video_id,
                "commentary",
                pct,
                f"実況生成中: {plan_idx + 1}/{plan_count}",
            )
        prev_text = com_data["text"]

    db.commit()
    debug_recorder.save_step_io(
        "commentary_generation",
        input_data={"plan_count": plan_count},
        output_data={
            "commentary_count": len(commentary_debug_rows),
            "commentaries": commentary_debug_rows,
        },
    )
    perf_recorder.finalize(
        {
            "status": "ok",
            "video_id": current_video_id,
            "segment_count": len(seg_results),
            "event_count": len(all_events),
            "plan_count": len(plan_results),
            "processed_count": len(processed_segment_indexes),
            "reused_count": len(reused_segment_indexes),
            "failed_count": len(failed_segment_indexes),
            "rerun_failed_only": rerun_failed_only,
        }
    )
    update_progress(current_video_id, "done", 100, "処理完了")
    performance_log_path = str(
        Path(cfg.media_root) / current_video_id / "debug" / "performance.json"
    )
    result = {
        "status": "ok",
        "video_id": current_video_id,
        "plans": len(plan_results),
        "rerun_failed_only": rerun_failed_only,
        "processed_segments": sorted(processed_segment_indexes),
        "reused_segments": sorted(reused_segment_indexes),
        "failed_segments": sorted(failed_segment_indexes),
        "performance_log_path": performance_log_path,
    }
    debug_recorder.save_step_io(
        "process_result",
        input_data={"video_id": video_id},
        output_data=result,
    )
    return result


@router.post("/{video_id}/compose")
def compose_video(video_id: str, db: Session = Depends(get_db)) -> dict:
    """実況音声・字幕を合成して最終動画を出力する。

    Args:
        video_id: 合成対象動画の ID。
        db: 発話計画・実況・音声・字幕を参照/保存する DB セッション。

    Returns:
        出力動画のパスを含む結果辞書。
    """
    video = _get_video_or_404(db, video_id)
    current_video_id = str(video.id)

    cfg = get_runtime_settings(db)
    debug_recorder = PipelineDebugRecorder(cfg.media_root, str(video.id))

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
        .filter(UtterancePlan.video_id == video.id)
        .order_by(UtterancePlan.start_time)
        .all()
    )

    pending_entries: list[tuple[UtterancePlan, Commentary, AudioEntry]] = []
    audio_entries: list[AudioEntry] = []
    srt_paths: list[str] = []
    tts_debug_rows: list[dict[str, Any]] = []
    subtitle_debug_rows: list[dict[str, Any]] = []
    schedule_debug_rows: list[dict[str, Any]] = []
    plan_count = len(plans)
    update_progress(current_video_id, "compose", 0, "音声合成を開始...")

    try:
        for plan_idx, plan in enumerate(plans):
            commentary = (
                db.query(Commentary).filter(Commentary.utterance_plan_id == plan.id).first()
            )
            if not commentary:
                continue

            pct = int((plan_idx + 1) / plan_count * 80)
            update_progress(
                current_video_id, "tts", pct, f"音声合成中: {plan_idx + 1}/{plan_count}"
            )
            audio_path = str(Path(cfg.media_root) / str(commentary.id) / "audio.wav")
            instruct = _STYLE_INSTRUCT.get(commentary.style or "", "")
            speaker = _resolve_tts_speaker(commentary.style or "", cfg)
            duration = tts_client.synthesize(
                commentary.text,
                audio_path,
                speaker=speaker,
                instruct=instruct,
            )
            tts_debug_rows.append(
                {
                    "index": plan_idx,
                    "plan_id": str(plan.id),
                    "commentary_id": str(commentary.id),
                    "style": commentary.style,
                    "speaker": speaker,
                    "audio_path": audio_path,
                    "duration_seconds": duration,
                }
            )

            audio = Audio(
                commentary_id=commentary.id,
                tts_mode=cfg.tts_default_mode,
                speaker=speaker,
                language=cfg.tts_default_language,
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
            schedule_debug_rows.append(
                {
                    "index": index,
                    "plan_id": str(plan.id),
                    "old_start_time": plan.start_time,
                    "new_start_time": normalized.start_time,
                    "duration_seconds": normalized.duration_seconds,
                }
            )
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
            subtitle_debug_rows.append(
                {
                    "index": index,
                    "commentary_id": str(commentary.id),
                    "file_path": srt_result.file_path,
                    "start_time": srt_result.start_time,
                    "end_time": srt_result.end_time,
                }
            )
            audio_entries.append(
                AudioEntry(
                    audio_path=normalized.audio_path,
                    start_time=normalized.start_time,
                    duration_seconds=normalized.duration_seconds,
                )
            )
            srt_paths.append(srt_result.file_path)

        db.commit()
        debug_recorder.save_step_io(
            "tts_and_subtitle",
            input_data={
                "plan_count": plan_count,
                "overlap_min_gap_seconds": cfg.compose_overlap_min_gap_seconds,
            },
            output_data={
                "tts_count": len(tts_debug_rows),
                "subtitle_count": len(subtitle_debug_rows),
                "schedule_count": len(schedule_debug_rows),
                "tts_items": tts_debug_rows,
                "schedule_items": schedule_debug_rows,
                "subtitle_items": subtitle_debug_rows,
            },
        )

        update_progress(current_video_id, "compose", 85, "字幕・動画を合成準備中...")
        update_progress(current_video_id, "compose", 88, "字幕ファイルを結合中...")
        merged_srt = _merge_srt(srt_paths, current_video_id, cfg.media_root)
        update_progress(current_video_id, "compose", 92, "映像・音声を合成中（FFmpeg）...")
        output_path = str(Path(cfg.media_root) / current_video_id / "output.mp4")
        composer.compose(video.storage_path, audio_entries, merged_srt, output_path)
        debug_recorder.save_step_io(
            "compose",
            input_data={
                "video_id": video_id,
                "video_id_normalized": current_video_id,
                "input_video": video.storage_path,
                "audio_count": len(audio_entries),
                "merged_srt": merged_srt,
            },
            output_data={"output_path": output_path},
        )
        update_progress(current_video_id, "compose", 98, "最終処理中...")

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        logger.error("FFmpeg 合成失敗: %s", stderr)
        raise HTTPException(status_code=500, detail=f"FFmpeg エラー: {stderr[:500]}") from e
    except Exception as e:
        logger.error("合成エラー: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

    logger.info("合成完了: %s", output_path)
    update_progress(current_video_id, "done", 100, "合成完了")
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

    Args:
        video_id: エクスポート対象動画の ID。
        db: 関連レコードを取得する DB セッション。

    Returns:
        ZIP ファイルを返すストリーミングレスポンス。
    """
    video = _get_video_or_404(db, video_id)
    current_video_id = str(video.id)

    plans = (
        db.query(UtterancePlan)
        .filter(UtterancePlan.video_id == video.id)
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
    filename = f"aituber_export_{current_video_id[:8]}.zip"
    logger.info("エクスポート: %s (%d 発話)", filename, len(csv_rows))
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _parse_video_uuid(video_id: str) -> uuid.UUID:
    """動画ID文字列をUUIDへ変換する。

    Args:
        video_id: パスパラメータで受け取った動画ID文字列。

    Returns:
        正常に変換された `UUID` オブジェクト。

    Raises:
        HTTPException: UUID形式でない場合。
    """
    try:
        return uuid.UUID(video_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="動画が見つかりません") from e


def _get_video_or_404(db: Session, video_id: str) -> Video:
    """動画IDから動画レコードを取得し、未存在時は404を送出する。

    Args:
        db: 動画取得に利用する DB セッション。
        video_id: 文字列形式の動画ID。

    Returns:
        取得した `Video` モデル。

    Raises:
        HTTPException: 動画ID形式が不正、または動画が存在しない場合。
    """
    parsed_video_id = _parse_video_uuid(video_id)
    video = db.query(Video).filter(Video.id == parsed_video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    return video


def _find_segment_by_time(
    db: Session,
    video_id: Any,
    start_time: float,
    end_time: float,
    tolerance: float = 1e-6,
) -> Segment | None:
    """開始/終了時刻で既存セグメントを検索する。

    Args:
        db: 検索対象セグメントを取得する DB セッション。
        video_id: 検索対象動画 ID。
        start_time: 探索対象の開始時刻（秒）。
        end_time: 探索対象の終了時刻（秒）。
        tolerance: 浮動小数誤差を吸収する許容差。

    Returns:
        一致するセグメント。存在しない場合は `None`。
    """
    segments = db.query(Segment).filter(Segment.video_id == video_id).all()
    for segment in segments:
        if (
            abs(segment.start_time - start_time) <= tolerance
            and abs(segment.end_time - end_time) <= tolerance
        ):
            return segment
    return None


def _events_to_results(events: list[Event], speak_threshold: float) -> list[EventResult]:
    """DB Event を UtterancePlanner 用 EventResult に変換する。

    Args:
        events: DB から読み出した `Event` モデル一覧。
        speak_threshold: 発話推奨フラグを立てる重要度閾値。

    Returns:
        `UtterancePlanner` が扱える `EventResult` の一覧。
    """
    results: list[EventResult] = []
    for event in events:
        importance = event.importance or 0.0
        results.append(
            EventResult(
                event_id=str(event.id),
                timestamp=event.timestamp,
                event_type=event.event_type,
                importance=importance,
                emotion_hint=_resolve_emotion_hint(importance),
                speak_recommended=importance >= speak_threshold,
                details=event.details or {},
            )
        )
    return results


def _resolve_emotion_hint(importance: float) -> str:
    """重要度から感情ラベルを返す。

    Args:
        importance: イベント重要度（0.0〜1.0 想定）。

    Returns:
        重要度帯に応じた感情ヒント（`excited` / `neutral` / `calm`）。
    """
    if importance >= 0.8:
        return "excited"
    if importance >= 0.5:
        return "neutral"
    return "calm"


def _probe_video_meta(video_path: str) -> tuple[float, float]:
    """動画メタ情報（duration, fps）を返す。

    Args:
        video_path: メタ情報を取得する動画ファイルパス。

    Returns:
        `(duration_seconds, fps)` のタプル。
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    duration = frame_count / fps if fps > 0 else 0.0
    return duration, fps


def _merge_srt(srt_paths: list[str], video_id: str, media_root: str) -> str | None:
    """SRT ファイル群を連結して1つの字幕ファイルへまとめる。

    Args:
        srt_paths: 結合候補の SRT ファイルパス一覧。
        video_id: 出力先ディレクトリ名に使う動画 ID。
        media_root: メディアルートディレクトリ。

    Returns:
        結合後 SRT ファイルパス。入力が空なら `None`。
    """
    valid = [p for p in srt_paths if Path(p).exists()]
    if not valid:
        return None
    merged_path = Path(media_root) / video_id / "merged.srt"
    with open(merged_path, "w", encoding="utf-8") as out:
        for path in valid:
            out.write(Path(path).read_text(encoding="utf-8"))
    return str(merged_path)


def _normalize_tags(tags: list[str]) -> list[str]:
    """タグ配列を大小文字非依存で重複排除して返す。

    Args:
        tags: ユーザー入力などのタグ文字列一覧。

    Returns:
        前後空白除去・大文字小文字非依存重複排除後のタグ一覧。
    """
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
    """動画からサムネイル画像を1枚生成する。

    Args:
        video_path: 入力動画ファイルパス。
        thumbnail_path: 書き出すサムネイル画像パス。

    Returns:
        なし。
    """
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
    """動画レスポンス用にタグメタデータを正規化する。

    Args:
        video: レスポンスへ変換する `Video` モデル。

    Returns:
        正規化済みメタデータを含む `VideoRead`。
    """
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
    """RuleTagger で自動タグを更新する。

    Args:
        video: タグ更新対象の動画モデル。
        cfg: ランタイム設定。TTS/LLM/VLM の既定値を参照する。

    Returns:
        `tags_auto_rule` と `tag_status.rule` を更新したメタデータ。
    """
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


def _resolve_tts_speaker(style: str, cfg: Any) -> str:
    """実況スタイルに対応するTTS話者名を返す。

    Args:
        style: 実況スタイル（`excited` / `neutral` / `calm`）。
        cfg: スタイル別話者設定を含むランタイム設定。

    Returns:
        スタイルに対応する話者名。未設定時はデフォルト話者名。
    """
    style_key = (style or "").strip().lower()
    speaker_map = {
        "excited": str(getattr(cfg, "tts_speaker_excited", "") or "").strip(),
        "neutral": str(getattr(cfg, "tts_speaker_neutral", "") or "").strip(),
        "calm": str(getattr(cfg, "tts_speaker_calm", "") or "").strip(),
    }
    return speaker_map.get(style_key) or str(cfg.tts_default_speaker)


def _to_video_tag_read(raw_metadata: dict[str, Any] | None) -> VideoTagRead:
    """タグ情報の API レスポンスを構築する。

    Args:
        raw_metadata: DB に保存されている生の動画メタデータ。

    Returns:
        API 返却用に正規化・集約したタグ情報。
    """
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
