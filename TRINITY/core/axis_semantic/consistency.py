"""시공간 일관성 (영상 전용).

전처리가 구간(start/middle/end)마다 연속 프레임 묶음을 주면, 인접 프레임 쌍에서
  - 정체성 흔들림: 인코더 특징(없으면 에지 구조) 간 거리의 불안정성
  - 시간 에너지 비율: 공간 구조 대비 시간 변화량과 그 요동(깜빡임)
  - NSG 근사: 밝기 기반 시공간 그래디언트 비율의 공간적 비일관성
을 잰다. 장면 전환(컷) 쌍은 제외하고 신뢰도를 낮춘다.

NSG 고지: 원 논문(NeurIPS 2025)은 사전학습 확산 모델로 공간 확률 그래디언트를 추정한다.
엣지 서버에서 프레임마다 확산 모델을 돌릴 수 없어 밝기 그래디언트 비율로 근사하며,
원 논문의 성능을 담보하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from core.contracts import Frame

from .encoders import VisionEncoder

CUT_THRESHOLD = 0.5    # 히스토그램 L1 거리 — 넘으면 장면 전환
ANALYSIS_SIDE = 160    # 시간 분석용 축소 크기 (주파수 분석이 아니므로 축소 허용)

# 재보정 대상: 각 지표가 이 값이면 해당 항 점수 0.5
FLICKER_MID = 0.35
JITTER_MID = 0.08
NSG_MID = 1.2


@dataclass
class ConsistencyReport:
    pairs: int
    cuts: int
    flicker: float           # 시간 에너지 비율의 변동계수
    jitter: float            # 정체성 거리의 표준편차
    nsg_incoherence: float   # 그래디언트 비율의 공간 비일관성 중앙값
    temporal_energy: list[float] = field(default_factory=list)

    @property
    def score(self) -> float:
        terms = [_sig(self.flicker / FLICKER_MID), _sig(self.jitter / JITTER_MID),
                 _sig(self.nsg_incoherence / NSG_MID)]
        return float(np.mean(terms))

    @property
    def confidence(self) -> float:
        if self.pairs == 0:
            return 0.0
        coverage = min(self.pairs / 12, 1.0)
        cut_penalty = 1.0 - min(self.cuts / max(self.pairs + self.cuts, 1), 1.0)
        return float(coverage * cut_penalty)


def _sig(ratio: float) -> float:
    """ratio=1에서 0.5가 되는 로지스틱."""
    return float(1.0 / (1.0 + np.exp(-4.0 * (ratio - 1.0))))


def _shrink(gray: np.ndarray) -> np.ndarray:
    step = max(1, int(np.ceil(max(gray.shape) / ANALYSIS_SIDE)))
    h, w = (gray.shape[0] // step) * step, (gray.shape[1] // step) * step
    return gray[:h, :w].reshape(h // step, step, w // step, step).mean((1, 3))


def _hist(gray: np.ndarray) -> np.ndarray:
    h, _ = np.histogram(gray, bins=32, range=(0, 255))
    return h / max(h.sum(), 1)


def _grad(g: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gy, gx = np.gradient(g)
    return gx, gy


def _edge_signature(g: np.ndarray) -> np.ndarray:
    gx, gy = _grad(g)
    e = np.hypot(gx, gy).ravel()
    e = e - e.mean()
    return e / (np.linalg.norm(e) + 1e-9)


def _nsg_incoherence(a: np.ndarray, b: np.ndarray) -> float:
    """밝기 항등식 It + ∇I·v ≈ 0 에서 |It|/|∇I| 는 국소 속도 크기의 근사.
    실제 움직임은 이 값이 공간적으로 매끄럽고, 생성물은 국소적으로 튄다.
    강한 그래디언트 화소에서 4-이웃 차분의 상대 크기를 잰다."""
    gx, gy = _grad((a + b) / 2)
    mag = np.hypot(gx, gy)
    it = np.abs(b - a)
    strong = mag > np.percentile(mag, 75)
    if strong.sum() < 16:
        return 0.0
    ratio = np.where(strong, it / (mag + 1e-6), np.nan)
    dx = np.abs(np.diff(ratio, axis=1))
    dy = np.abs(np.diff(ratio, axis=0))
    diffs = np.concatenate([dx[~np.isnan(dx)], dy[~np.isnan(dy)]])
    if diffs.size == 0:
        return 0.0
    local = np.median(diffs)
    level = np.nanmedian(ratio) + 1e-3
    return float(local / level)


def analyze_segments(segments: dict[str, list[Frame]],
                     encoder: VisionEncoder | None = None) -> ConsistencyReport:
    energies, dists, nsg = [], [], []
    pairs = cuts = 0
    for frames in segments.values():
        frames = sorted(frames, key=lambda f: f.index)
        if len(frames) < 2:
            continue
        grays = [_shrink(f.gray) for f in frames]
        if encoder is not None:
            sigs = list(encoder.encode([f.pixels for f in frames]))
        else:
            sigs = [_edge_signature(g) for g in grays]
        for i in range(len(frames) - 1):
            a, b = grays[i], grays[i + 1]
            if np.abs(_hist(a) - _hist(b)).sum() > CUT_THRESHOLD:
                cuts += 1
                continue
            pairs += 1
            gx, gy = _grad(a)
            energies.append(float(np.abs(b - a).mean() / (np.hypot(gx, gy).mean() + 1e-6)))
            dists.append(float(1.0 - np.dot(sigs[i], sigs[i + 1])))
            nsg.append(_nsg_incoherence(a, b))

    if pairs == 0:
        return ConsistencyReport(0, cuts, 0.0, 0.0, 0.0)
    e = np.array(energies)
    flicker = float(e.std() / (e.mean() + 1e-6)) if pairs > 1 else 0.0
    jitter = float(np.std(dists)) if pairs > 1 else 0.0
    return ConsistencyReport(pairs, cuts, flicker, jitter, float(np.median(nsg)),
                             temporal_energy=[round(x, 4) for x in energies])
