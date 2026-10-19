"""제1축: 신호(주파수).

규칙 기반 스코어러(1-A)는 항상 동작하고, 학습 모델(1-B)은 가중치가 있을 때만 합류한다.
"""
from __future__ import annotations

from pathlib import Path

from core.contracts import AxisName, AxisResult, FrameBundle

from .hybrid_attention import HybridSignalModel
from .statistical import StatisticalSignalScorer

# 1-B가 가용할 때 두 스코어러의 혼합 비율
HYBRID_WEIGHT = 0.6


class SignalAxis:
    name = AxisName.SIGNAL

    def __init__(self, hybrid_weights: Path | None = None):
        self.statistical = StatisticalSignalScorer()
        self.hybrid = HybridSignalModel(hybrid_weights)

    def analyze(self, bundle: FrameBundle) -> AxisResult:
        base = self.statistical.analyze(bundle)
        if not (base.usable and self.hybrid.available):
            return base
        learned = self.hybrid.analyze(bundle)
        if not learned.usable:
            return base
        w = HYBRID_WEIGHT
        base.score = (1 - w) * base.score + w * learned.score
        base.confidence = (1 - w) * base.confidence + w * learned.confidence
        base.evidence += learned.evidence
        base.details["hybrid"] = learned.details
        return base


__all__ = ["SignalAxis", "StatisticalSignalScorer", "HybridSignalModel"]
