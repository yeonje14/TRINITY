"""동적 가중 앙상블.

기본 가중치 신호 0.40 / 출처 0.35 / 의미 0.25에서 시작해 조건별로 재조정한다 (README §3 융합).

| 조건                 | 동작                                                     |
|----------------------|----------------------------------------------------------|
| 제2축 양성           | 출처 가중 0.60 + 타 축 교차 확인 — 즉시 확정하지 않음    |
| 무결성 충돌 감지     | 세탁 의심으로 위험도 한 단계 승격 (최소 '주의')          |
| 제2축 음성           | 출처 가중 0 → 제1·3축 융합이 주력                        |
| 저화질/블러 입력     | 제1축 ×0.5, 제3축 ×1.4                                   |
| 축 적용 불가         | 가중 0 + 게이트 사유 반환                                |
| 근거 빈약(신뢰도<0.3)| 점수가 낮아도 '안전'으로 단정하지 않고 '주의'            |
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from core.contracts import AxisName, AxisResult, Evidence, QualityMetrics

BASE_WEIGHTS = {AxisName.SIGNAL: 0.40, AxisName.PROVENANCE: 0.35, AxisName.SEMANTIC: 0.25}
PROVENANCE_POSITIVE_WEIGHT = 0.60
LOW_QUALITY_SIGNAL = 0.5
LOW_QUALITY_SEMANTIC = 1.4

CAUTION_AT = 0.4
HIGH_AT = 0.7
MIN_CONFIDENCE = 0.3
CROSS_CHECK_AT = 0.5  # 출처 양성일 때 타 축이 이 이상이면 '교차 확인됨'


class RiskLevel(str, Enum):
    LOW = "low"         # 낮음 (초록)
    CAUTION = "caution" # 주의 (노랑)
    HIGH = "high"       # 높음 (빨강)


_ORDER = [RiskLevel.LOW, RiskLevel.CAUTION, RiskLevel.HIGH]


@dataclass
class EnsembleResult:
    score: float | None
    level: RiskLevel
    confidence: float
    weights: dict[AxisName, float]
    axes: dict[AxisName, AxisResult]
    gates: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


def _level(score: float) -> RiskLevel:
    if score >= HIGH_AT:
        return RiskLevel.HIGH
    if score >= CAUTION_AT:
        return RiskLevel.CAUTION
    return RiskLevel.LOW


def _bump(level: RiskLevel, minimum: RiskLevel = RiskLevel.CAUTION) -> RiskLevel:
    up = _ORDER[min(_ORDER.index(level) + 1, len(_ORDER) - 1)]
    return max(up, minimum, key=_ORDER.index)


class DynamicEnsemble:
    def fuse(self, results: list[AxisResult], quality: QualityMetrics) -> EnsembleResult:
        axes = {r.axis: r for r in results}
        weights = dict(BASE_WEIGHTS)
        gates: list[str] = []
        flags: list[str] = []
        evidence: list[Evidence] = []

        for name in BASE_WEIGHTS:
            r = axes.get(name)
            if r is None or not r.usable:
                weights[name] = 0.0
                reason = r.gate_reason if r and r.gate_reason else (
                    r.status.value if r else "실행되지 않음")
                gates.append(f"{name.value}: {reason}")

        prov = axes.get(AxisName.PROVENANCE)
        prov_positive = prov is not None and prov.usable
        laundering = bool(prov and prov.details.get("laundering_suspected"))

        if quality.low_quality:
            weights[AxisName.SIGNAL] *= LOW_QUALITY_SIGNAL
            weights[AxisName.SEMANTIC] *= LOW_QUALITY_SEMANTIC
            flags.append("low_quality")

        weights = self._normalize(weights, prov_positive)

        if not any(weights.values()):
            return EnsembleResult(None, RiskLevel.CAUTION, 0.0, weights, axes,
                                  gates, flags + ["no_usable_axis"],
                                  [Evidence("ensemble.no_axis",
                                            "사용 가능한 분석 축이 없어 판단을 보류합니다", None)])

        score = sum(weights[n] * axes[n].score for n, w in weights.items() if w)
        confidence = sum(weights[n] * axes[n].confidence for n, w in weights.items() if w)
        level = _level(score)

        if prov_positive:
            others = [axes[n] for n in (AxisName.SIGNAL, AxisName.SEMANTIC)
                      if weights.get(n) and axes[n].usable]
            if any(o.score >= CROSS_CHECK_AT for o in others):
                flags.append("provenance_cross_checked")
            else:
                flags.append("provenance_uncorroborated")
                confidence *= 0.8
                evidence.append(Evidence(
                    "ensemble.uncorroborated",
                    "출처 신호는 양성이나 신호·의미 축이 뒷받침하지 않음 — 워터마크 스푸핑 가능성 고려", None))

        if laundering:
            flags.append("laundering_suspected")
            level = _bump(level)
            evidence.append(Evidence(
                "ensemble.laundering", "무결성 충돌 — 출처 세탁 의심으로 위험도 승격", True))

        if confidence < MIN_CONFIDENCE and level is RiskLevel.LOW:
            level = RiskLevel.CAUTION
            flags.append("low_confidence")
            evidence.append(Evidence(
                "ensemble.low_confidence", "근거가 빈약해 '안전'으로 단정하지 않습니다", None))

        return EnsembleResult(float(score), level, float(confidence), weights, axes,
                              gates, flags, evidence)

    @staticmethod
    def _normalize(weights: dict[AxisName, float], prov_positive: bool) -> dict[AxisName, float]:
        if prov_positive:
            rest = {n: w for n, w in weights.items() if n is not AxisName.PROVENANCE}
            total = sum(rest.values())
            if total == 0:
                return {**{n: 0.0 for n in rest}, AxisName.PROVENANCE: 1.0}
            remaining = 1.0 - PROVENANCE_POSITIVE_WEIGHT
            return {**{n: remaining * w / total for n, w in rest.items()},
                    AxisName.PROVENANCE: PROVENANCE_POSITIVE_WEIGHT}
        total = sum(weights.values())
        return {n: (w / total if total else 0.0) for n, w in weights.items()}
