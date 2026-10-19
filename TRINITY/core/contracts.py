"""축 공용 인터페이스 계약.

세 축은 서로를 import하지 않고 이 모듈의 타입만 주고받는다.
전처리는 FrameBundle을 만들고, 각 축은 AxisResult를 돌려주며, 앙상블은 AxisResult만 본다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import numpy as np


class Track(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class AxisName(str, Enum):
    SIGNAL = "signal"
    PROVENANCE = "provenance"
    SEMANTIC = "semantic"


class AxisStatus(str, Enum):
    OK = "ok"                          # 점수 산출됨
    NO_EVIDENCE = "no_evidence"        # 실행했으나 증거 없음 (제2축 음성 — 진본 증명 아님)
    NOT_APPLICABLE = "not_applicable"  # 입력 특성상 적용 불가 (예: 이미지에 시간축 분석)
    UNAVAILABLE = "unavailable"        # 모델·탐지기 미연결
    ERROR = "error"


@dataclass(frozen=True)
class Frame:
    """한 장의 프레임. pixels는 원본 해상도 RGB uint8 (H, W, 3) — 리사이즈 금지."""

    pixels: np.ndarray
    index: int = 0
    timestamp: float | None = None
    segment: str = "image"  # image | start | middle | end
    patches: tuple[np.ndarray, ...] = ()  # 원본 해상도에서 잘라낸 분석용 패치

    @property
    def gray(self) -> np.ndarray:
        p = self.pixels.astype(np.float32)
        return 0.299 * p[..., 0] + 0.587 * p[..., 1] + 0.114 * p[..., 2]


@dataclass(frozen=True)
class QualityMetrics:
    width: int
    height: int
    sharpness: float      # 라플라시안 분산 — 낮을수록 블러
    blockiness: float     # 8x8 블록 경계 불연속 비율 — 높을수록 강한 압축
    low_quality: bool     # 앙상블에서 제1축 하향 게이팅에 사용


@dataclass
class FrameBundle:
    track: Track
    frames: list[Frame]
    quality: QualityMetrics
    source_path: Path | None = None   # 제2축(C2PA)이 컨테이너를 직접 읽을 때 사용
    raw_bytes: bytes | None = None
    metadata: dict[str, Any] = field(default_factory=dict)  # channel_id, title, fps 등

    def segments(self) -> dict[str, list[Frame]]:
        out: dict[str, list[Frame]] = {}
        for f in self.frames:
            out.setdefault(f.segment, []).append(f)
        return out


@dataclass(frozen=True)
class Evidence:
    """사용자에게 보여줄 판단 근거 한 줄."""

    code: str
    message: str
    supports_ai: bool | None = None  # True: AI 쪽 근거, False: 실촬영 쪽 근거, None: 중립·주의


@dataclass
class AxisResult:
    axis: AxisName
    status: AxisStatus
    score: float | None = None  # 0(실촬영) ~ 1(AI 생성)
    confidence: float = 0.0     # 0 ~ 1
    evidence: list[Evidence] = field(default_factory=list)
    gate_reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return self.status is AxisStatus.OK and self.score is not None


@runtime_checkable
class Axis(Protocol):
    name: AxisName

    def analyze(self, bundle: FrameBundle) -> AxisResult: ...
