"""요청·응답 스키마 (Flutter 클라이언트와의 계약)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from core.contracts import AxisName, AxisStatus, Track
from core.ensemble import RiskLevel


class AnalyzeUrlRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def _youtube_only(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("http(s) URL이어야 합니다")
        if not any(h in v for h in ("youtube.com/", "youtu.be/")):
            raise ValueError("현재는 유튜브 링크만 지원합니다")
        return v


class EvidenceOut(BaseModel):
    code: str
    message: str
    supports_ai: bool | None = None


class AxisOut(BaseModel):
    axis: AxisName
    status: AxisStatus
    score: float | None
    confidence: float
    weight: float
    gate_reason: str | None = None
    evidence: list[EvidenceOut] = []
    details: dict[str, Any] = {}


class SourceInfo(BaseModel):
    url: str | None = None
    video_id: str | None = None
    channel_id: str | None = None
    channel: str | None = None
    title: str | None = None
    filename: str | None = None


class AnalysisResult(BaseModel):
    id: str
    track: Track
    risk_level: RiskLevel
    score: float | None
    confidence: float
    axes: list[AxisOut]
    flags: list[str] = []
    gates: list[str] = []
    evidence: list[EvidenceOut] = []
    quality: dict[str, Any] = {}
    source: SourceInfo = SourceInfo()
    created_at: datetime
    disclaimer: str = "위험도 점수이며 단정적 판정이 아닙니다. 임계값은 실제 데이터셋 재보정 전입니다."


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class JobCreated(BaseModel):
    job_id: str


class JobOut(BaseModel):
    job_id: str
    state: JobState
    progress: float = Field(ge=0, le=1)
    stage: str | None = None
    result: AnalysisResult | None = None
    error: str | None = None


class HistoryItem(BaseModel):
    id: str
    track: Track
    risk_level: RiskLevel
    score: float | None
    title: str | None = None
    channel_id: str | None = None
    created_at: datetime


class ChannelSummary(BaseModel):
    channel_id: str
    channel: str | None
    analyzed: int
    high_risk: int
    caution: int
    recent: list[HistoryItem]
