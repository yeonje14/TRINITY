"""축1-A: 규칙 기반 스코어러 (학습 불필요).

패치마다 스펙트럼 특징을 뽑아 점수를 매기고 중앙값으로 집계한다.
계수는 합성 데이터에서 판정 '순서'만 맞춘 초기값이며, 실제 벤치마크로 재보정해야 한다 (README §10).
"""
from __future__ import annotations

import numpy as np

from core.contracts import AxisName, AxisResult, AxisStatus, Evidence, FrameBundle

from .spectrum import SpectrumFeatures, analyze_patch

# 재보정 대상 계수
GRID_SCALE = 20.0       # grid_strength가 이 정도면 격자 항이 ~0.63
HF_EXCESS_SCALE = 0.5   # log10 단위 고대역 초과량
W_GRID = 0.7
W_HF = 0.3


def score_features(f: SpectrumFeatures) -> float:
    g = 1.0 - np.exp(-f.grid_strength / GRID_SCALE)
    h = float(np.clip(f.hf_excess / HF_EXCESS_SCALE, 0.0, 1.0))
    return float(np.clip(W_GRID * g + W_HF * h, 0.0, 1.0))


class StatisticalSignalScorer:
    name = AxisName.SIGNAL

    def __init__(self, max_patches: int = 24):
        self.max_patches = max_patches

    def analyze(self, bundle: FrameBundle) -> AxisResult:
        patches = [p for f in bundle.frames for p in (f.patches or (f.pixels,))]
        if not patches:
            return AxisResult(self.name, AxisStatus.NOT_APPLICABLE, gate_reason="분석할 프레임 없음")
        patches = patches[: self.max_patches]

        feats = [analyze_patch(_gray(p)) for p in patches]
        scores = np.array([score_features(f) for f in feats])
        score = float(np.median(scores))

        # 패치 간 합의도 × 표본 수 × 화질
        agreement = 1.0 - min(float(np.std(scores)) * 2, 1.0)
        coverage = min(len(scores) / 8, 1.0)
        confidence = agreement * (0.5 + 0.5 * coverage)
        if bundle.quality.low_quality:
            confidence *= 0.5

        evidence = []
        on_grid = sum(f.on_grid_count for f in feats)
        if on_grid:
            evidence.append(Evidence(
                "signal.grid_peaks",
                f"업샘플링 격자 위치에서 주기적 스펙트럼 피크 {on_grid}개 검출", True))
        mean_excess = float(np.mean([f.hf_excess for f in feats]))
        if mean_excess > HF_EXCESS_SCALE * 0.5:
            evidence.append(Evidence(
                "signal.hf_excess", "고주파 대역이 자연 영상의 멱법칙 분포보다 과도함", True))
        if not evidence:
            evidence.append(Evidence(
                "signal.clean", "주기적 격자 흔적이 관측되지 않음", False))
        if bundle.quality.low_quality:
            evidence.append(Evidence(
                "signal.low_quality", "저화질·블러 입력 — 주파수 단서 신뢰도 하향", None))

        return AxisResult(
            self.name, AxisStatus.OK, score=score, confidence=float(confidence),
            evidence=evidence,
            details={
                "scorer": "statistical",
                "patches": len(scores),
                "patch_scores": scores.round(4).tolist(),
                "mean_slope": float(np.mean([f.powerlaw_slope for f in feats])),
                "mean_hf_excess": mean_excess,
                "on_grid_peaks": on_grid,
                "off_grid_peaks": sum(f.off_grid_count for f in feats),
            },
        )


def _gray(rgb: np.ndarray) -> np.ndarray:
    if rgb.ndim == 2:
        return rgb.astype(np.float32)
    p = rgb.astype(np.float32)
    return 0.299 * p[..., 0] + 0.587 * p[..., 1] + 0.114 * p[..., 2]
