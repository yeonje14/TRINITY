"""제2축: 출처 증명.

양성은 강한 증거, 음성은 무정보 — 그리고 양성조차 절대적이지 않다.
양성이어도 즉시 확정(Early-Exit)하지 않는다: mark-to-frame 스푸핑으로 진짜 미디어에
워터마크를 덧칠할 수 있기 때문 (arXiv:2606.23335). 최종 판단은 앙상블이 타 축과 교차해 내린다.
"""
from __future__ import annotations

from core.contracts import AxisName, AxisResult, AxisStatus, Evidence, FrameBundle, Track

from .audit import AuditOutcome, AuditVerdict, audit
from .c2pa import read_manifest
from .synthid import UnavailableDetector, WatermarkDetector, scan_frames


class ProvenanceAxis:
    name = AxisName.PROVENANCE

    def __init__(self, detector: WatermarkDetector | None = None):
        self.detector = detector or UnavailableDetector()

    def analyze(self, bundle: FrameBundle) -> AxisResult:
        manifest = read_manifest(bundle.source_path, bundle.raw_bytes)
        watermark = scan_frames(self.detector, [f.pixels for f in bundle.frames],
                                is_video=bundle.track is Track.VIDEO)
        outcome = audit(manifest, watermark)
        details = {"verdict": outcome.verdict.value,
                   "laundering_suspected": outcome.laundering_suspected,
                   **outcome.details}

        if not outcome.positive:
            return AxisResult(
                self.name, AxisStatus.NO_EVIDENCE,
                evidence=[Evidence("provenance.none", outcome.message, None)],
                gate_reason="출처 신호 없음 (진본 증명 아님)", details=details)

        return AxisResult(
            self.name, AxisStatus.OK, score=outcome.score, confidence=outcome.confidence,
            evidence=[Evidence(f"provenance.{outcome.verdict.value}", outcome.message, True)],
            details=details)


__all__ = ["ProvenanceAxis", "AuditOutcome", "AuditVerdict", "audit"]
