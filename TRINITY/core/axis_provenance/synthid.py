"""워터마크 탐지기 플러그인 슬롯.

SynthID 검출은 구글 비공개 인프라가 필요해 제3자 독립 구현이 불가능하다.
Content Detection API 승인 전까지는 인터페이스만 두고, 기본 탐지기는 UNAVAILABLE을 반환한다.

UNAVAILABLE(탐지기 미연결)과 NOT_DETECTED(스캔했으나 미발견)는 엄격히 구분한다.
둘 다 '진짜'를 뜻하지 않지만 의미가 다르다.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import numpy as np

# 영상 프레임별 검출률 구간 — 사이 값은 부분 합성 의심
PARTIAL_LOW = 0.2
PARTIAL_HIGH = 0.8


class WatermarkStatus(str, Enum):
    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    PARTIAL = "partial"          # 영상 전용: 일부 프레임에서만 검출
    UNAVAILABLE = "unavailable"


@dataclass
class WatermarkResult:
    status: WatermarkStatus
    detector: str
    detection_rate: float | None = None  # 검출 프레임 비율 (영상)
    frames_scanned: int = 0


class WatermarkDetector(Protocol):
    name: str

    def detect_frame(self, rgb: np.ndarray) -> bool | None:
        """True: 검출, False: 미검출, None: 이 프레임은 판정 불가."""
        ...


class UnavailableDetector:
    name = "none"

    def detect_frame(self, rgb: np.ndarray) -> bool | None:
        return None


def scan_frames(detector: WatermarkDetector, frames: list[np.ndarray],
                is_video: bool) -> WatermarkResult:
    if isinstance(detector, UnavailableDetector) or not frames:
        return WatermarkResult(WatermarkStatus.UNAVAILABLE, detector.name)

    hits = [r for r in (detector.detect_frame(f) for f in frames) if r is not None]
    if not hits:
        return WatermarkResult(WatermarkStatus.UNAVAILABLE, detector.name)

    rate = sum(hits) / len(hits)
    if not is_video:
        status = WatermarkStatus.DETECTED if rate >= 0.5 else WatermarkStatus.NOT_DETECTED
    elif rate > PARTIAL_HIGH:
        status = WatermarkStatus.DETECTED
    elif rate >= PARTIAL_LOW:
        status = WatermarkStatus.PARTIAL
    else:
        status = WatermarkStatus.NOT_DETECTED
    return WatermarkResult(status, detector.name, rate, len(hits))
