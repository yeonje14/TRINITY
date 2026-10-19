import pytest

from core.contracts import AxisName, AxisResult, AxisStatus, QualityMetrics
from core.ensemble import DynamicEnsemble, RiskLevel

GOOD = QualityMetrics(1920, 1080, 500.0, 1.0, False)
LOW = QualityMetrics(320, 240, 10.0, 2.0, True)
S, P, M = AxisName.SIGNAL, AxisName.PROVENANCE, AxisName.SEMANTIC


def ok(axis, score, conf=0.8, **details):
    return AxisResult(axis, AxisStatus.OK, score=score, confidence=conf, details=details)


def none(axis, status=AxisStatus.NO_EVIDENCE):
    return AxisResult(axis, status, gate_reason="test gate")


def fuse(results, q=GOOD):
    return DynamicEnsemble().fuse(results, q)


def test_negative_provenance_gets_zero_weight():
    r = fuse([ok(S, 0.2), none(P), ok(M, 0.2)])
    assert r.weights[P] == 0
    assert r.weights[S] == pytest.approx(0.40 / 0.65)
    assert r.level is RiskLevel.LOW
    assert any("provenance" in g for g in r.gates)


def test_positive_provenance_weight_and_no_early_exit():
    r = fuse([ok(S, 0.1), ok(P, 0.95), ok(M, 0.1)])
    assert r.weights[P] == pytest.approx(0.60)
    assert sum(r.weights.values()) == pytest.approx(1.0)
    assert r.score < 0.95  # 즉시 확정하지 않는다
    assert "provenance_uncorroborated" in r.flags


def test_positive_provenance_cross_checked():
    r = fuse([ok(S, 0.8), ok(P, 0.95), ok(M, 0.6)])
    assert "provenance_cross_checked" in r.flags
    assert r.level is RiskLevel.HIGH


def test_laundering_bumps_level():
    base = fuse([ok(S, 0.1), ok(P, 0.3), ok(M, 0.1)])
    laundered = fuse([ok(S, 0.1), ok(P, 0.3, laundering_suspected=True), ok(M, 0.1)])
    assert base.level is RiskLevel.LOW
    assert laundered.level is RiskLevel.CAUTION
    assert "laundering_suspected" in laundered.flags


def test_low_quality_shifts_weight_to_semantic():
    good = fuse([ok(S, 0.5), none(P), ok(M, 0.5)], GOOD)
    low = fuse([ok(S, 0.5), none(P), ok(M, 0.5)], LOW)
    assert low.weights[S] < good.weights[S]
    assert low.weights[M] > good.weights[M]


def test_low_confidence_never_reports_safe():
    r = fuse([ok(S, 0.05, conf=0.1), none(P), none(M, AxisStatus.UNAVAILABLE)])
    assert r.level is RiskLevel.CAUTION
    assert "low_confidence" in r.flags


def test_no_usable_axis():
    r = fuse([none(S, AxisStatus.ERROR), none(P), none(M, AxisStatus.UNAVAILABLE)])
    assert r.score is None and r.level is RiskLevel.CAUTION
    assert len(r.gates) == 3
