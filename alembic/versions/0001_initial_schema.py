"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("duration_seconds", sa.Float),
        sa.Column("fps", sa.Float),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_time", sa.Float, nullable=False),
        sa.Column("end_time", sa.Float, nullable=False),
        sa.Column("type", sa.Text, server_default="gameplay"),
        sa.Column("storage_path", sa.Text),
    )
    op.create_index("ix_segments_video_id", "segments", ["video_id"])

    op.create_table(
        "frames",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "segment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("segments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.Float, nullable=False),
        sa.Column("image_path", sa.Text),
        sa.Column("features", postgresql.JSONB, server_default="{}"),
    )
    op.create_index("ix_frames_segment_id", "frames", ["segment_id"])
    op.execute("CREATE INDEX ix_frames_features_gin ON frames USING GIN (features)")

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "segment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("segments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.Float, nullable=False),
        sa.Column("type", sa.Text, server_default="scene_change"),
        sa.Column("importance", sa.Float, server_default="0.5"),
        sa.Column("details", postgresql.JSONB, server_default="{}"),
    )
    op.create_index("ix_events_segment_id", "events", ["segment_id"])
    op.execute("CREATE INDEX ix_events_details_gin ON events USING GIN (details)")

    op.create_table(
        "utterance_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_ids", postgresql.JSONB, server_default="[]"),
        sa.Column("start_time", sa.Float, nullable=False),
        sa.Column("end_time", sa.Float, nullable=False),
        sa.Column("priority", sa.Integer, server_default="1"),
        sa.Column("style", sa.Text, server_default="calm"),
    )
    op.create_index("ix_utterance_plans_video_id", "utterance_plans", ["video_id"])

    op.create_table(
        "commentaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "utterance_plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("utterance_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("language", sa.Text, server_default="japanese"),
        sa.Column("style", sa.Text, server_default="calm"),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("llm_raw_response", postgresql.JSONB, server_default="{}"),
    )
    op.create_index("ix_commentaries_plan_id", "commentaries", ["utterance_plan_id"])

    op.create_table(
        "audios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "commentary_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("commentaries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tts_mode", sa.Text, server_default="custom_voice"),
        sa.Column("speaker", sa.Text, server_default="ono_anna"),
        sa.Column("language", sa.Text, server_default="japanese"),
        sa.Column("storage_path", sa.Text),
        sa.Column("duration_seconds", sa.Float),
    )
    op.create_index("ix_audios_commentary_id", "audios", ["commentary_id"])

    op.create_table(
        "subtitles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "commentary_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("commentaries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_path", sa.Text),
        sa.Column("start_time", sa.Float, nullable=False),
        sa.Column("end_time", sa.Float, nullable=False),
    )
    op.create_index("ix_subtitles_commentary_id", "subtitles", ["commentary_id"])


def downgrade() -> None:
    op.drop_table("subtitles")
    op.drop_table("audios")
    op.drop_table("commentaries")
    op.drop_table("utterance_plans")
    op.drop_table("events")
    op.drop_table("frames")
    op.drop_table("segments")
    op.drop_table("videos")
