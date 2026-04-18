"""Pydantic v2 response models shared across routers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChannelStats(_Base):
    """Snapshot of the channel's current headline statistics."""

    channel_id: str
    subscriber_count: int
    total_view_count: int
    video_count: int


class TimeseriesPoint(_Base):
    """A single datapoint on the channel-level subscriber/view timeline."""

    collected_at: str
    value: int


class VideoSummary(_Base):
    """Compact video record used in listings."""

    video_id: str
    title: str
    published_at: str
    view_count: int
    like_count: int
    comment_count: int


class VideoDetail(_Base):
    """Full detail for a single video, including duration."""

    video_id: str
    title: str
    published_at: str
    duration_sec: int
    view_count: int
    like_count: int
    comment_count: int


class VideoTimeseriesPoint(_Base):
    """Per-day analytics value for a single video."""

    date: str
    value: float


class TrafficSource(_Base):
    """Traffic-source breakdown item."""

    traffic_source_type: str
    views: int


class Demographic(_Base):
    """Viewer demographic slice by age group and gender."""

    age_group: str
    gender: str
    view_percentage: float


class RankingItem(_Base):
    """Video ranking row with rank and metric value."""

    rank: int
    video_id: str
    title: str
    published_at: str
    value: float


class CompareItem(_Base):
    """Single datapoint in the multi-video comparison response."""

    video_id: str
    title: str
    date: str
    value: float


class CollectResult(_Base):
    """Result payload for `POST /api/collect`."""

    status: str = Field(default="ok")
    collected_at: str
    subscriber_count: int
    total_view_count: int
