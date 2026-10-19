"""제3축: 의미·물리.

픽셀은 완벽해도, 의미의 분포와 물리 법칙은 속이기 어렵다.
  - 분포 편차: 인코더 + 참조 분포가 주입되어야 활성 (이미지·영상 공통)
  - 시공간 일관성: 영상 전용, 인코더 없이도 동작
스코프: 최신 서베이 4계층 중 1~2계층 + 분포 편차. 크로스모달·LLM 세계추론은 Future Work.
"""
from __future__ import annotations

import numpy as np

from core.contracts import AxisName, AxisResult, AxisStatus, Evidence, FrameBundle, Track

from .consistency import analyze_segments
from .distribution import ReferenceDistribution
from .encoders import VisionEncoder


class SemanticAxis:
    name = AxisName.SEMANTIC

    def __init__(self, encoder: VisionEncoder | None = None,
                 reference: ReferenceDistribution | None = None):
        self.encoder = encoder
        self.reference = reference

    def analyze(self, bundle: FrameBundle) -> AxisResult:
        parts: list[tuple[float, float]] = []  # (score, confidence)
        evidence: list[Evidence] = []
        details: dict = {}
        gates: list[str] = []

        if self.encoder is not None and self.reference is not None:
            feats = self.encoder.encode([f.pixels for f in bundle.frames])
            s = self.reference.score(feats)
            score = float(np.median(s))
            parts.append((score, 0.6))
            details["distribution_scores"] = s.round(4).tolist()
            evidence.append(Evidence(
                "semantic.distribution",
                "실제 이미지 특징 분포에서 크게 벗어남 (의미 성분 감산 후)" if score > 0.5
                else "실제 이미지 특징 분포 범위 안", score > 0.5))
        else:
            gates.append("분포 편차: 인코더·참조 분포 미주입")

        if bundle.track is Track.VIDEO:
            rep = analyze_segments(bundle.segments(), self.encoder)
            details["consistency"] = {
                "pairs": rep.pairs, "cuts": rep.cuts, "flicker": rep.flicker,
                "jitter": rep.jitter, "nsg_incoherence": rep.nsg_incoherence,
                "temporal_energy": rep.temporal_energy,
            }
            if rep.pairs:
                parts.append((rep.score, rep.confidence))
                evidence.append(Evidence(
                    "semantic.temporal",
                    "인접 프레임 간 시간 에너지·구조가 불안정함" if rep.score > 0.5
                    else "시공간 연속성이 안정적임", rep.score > 0.5))
                evidence.append(Evidence(
                    "semantic.nsg_approx", "NSG는 밝기 그래디언트 비율 근사치", None))
            else:
                gates.append("시공간 일관성: 비교 가능한 연속 프레임 없음")
            if rep.cuts:
                evidence.append(Evidence(
                    "semantic.scene_cut", f"장면 전환 {rep.cuts}회 감지 — 해당 구간 제외·신뢰도 하향", None))
        else:
            gates.append("시공간 일관성: 이미지 입력")

        details["gates"] = gates
        if not parts:
            return AxisResult(self.name, AxisStatus.UNAVAILABLE, evidence=evidence,
                              gate_reason="; ".join(gates), details=details)

        w = np.array([c for _, c in parts]) + 1e-6
        score = float(np.average([s for s, _ in parts], weights=w))
        confidence = float(np.mean([c for _, c in parts]))
        return AxisResult(self.name, AxisStatus.OK, score=score, confidence=confidence,
                          evidence=evidence, details=details)


__all__ = ["SemanticAxis", "ReferenceDistribution"]
