import pytest

from core.axis_provenance import ProvenanceAxis
from core.axis_provenance.audit import AuditVerdict, audit
from core.axis_provenance.c2pa import C2PAResult, ManifestClaim, ManifestState, scan_container
from core.axis_provenance.synthid import (UnavailableDetector, WatermarkResult, WatermarkStatus,
                                          scan_frames)
from core.contracts import AxisStatus
from preprocessing.ingest import bundle_from_image
from synthetic import natural, png_bytes

V, U, N, I = ManifestState.VALID, ManifestState.UNVERIFIED, ManifestState.NONE, ManifestState.INVALID
AI, HUMAN, UNK = ManifestClaim.AI_GENERATED, ManifestClaim.HUMAN, ManifestClaim.UNKNOWN
D, ND, P, NA = (WatermarkStatus.DETECTED, WatermarkStatus.NOT_DETECTED,
                WatermarkStatus.PARTIAL, WatermarkStatus.UNAVAILABLE)


@pytest.mark.parametrize("state,claim,wm,expected", [
    (I, UNK, NA, AuditVerdict.TAMPER_SUSPECTED),
    (I, HUMAN, D, AuditVerdict.TAMPER_SUSPECTED),
    (V, AI, D, AuditVerdict.CONSISTENT_AI),
    (V, AI, ND, AuditVerdict.WATERMARK_REMOVAL_SUSPECTED),
    (V, AI, NA, AuditVerdict.SINGLE_LAYER_MANIFEST),
    (V, HUMAN, D, AuditVerdict.INTEGRITY_CONFLICT),
    (V, HUMAN, P, AuditVerdict.INTEGRITY_CONFLICT),
    (V, HUMAN, ND, AuditVerdict.NO_INFORMATION),
    (V, HUMAN, NA, AuditVerdict.NO_INFORMATION),
    (N, UNK, D, AuditVerdict.SINGLE_LAYER_WATERMARK),
    (N, UNK, P, AuditVerdict.PARTIAL_SYNTHESIS),
    (V, AI, P, AuditVerdict.PARTIAL_SYNTHESIS),
    (N, UNK, ND, AuditVerdict.NO_INFORMATION),
    (N, UNK, NA, AuditVerdict.NO_INFORMATION),
])
def test_conflict_matrix(state, claim, wm, expected):
    out = audit(C2PAResult(state, claim), WatermarkResult(wm, "test"))
    assert out.verdict is expected
    assert out.positive == (expected is not AuditVerdict.NO_INFORMATION)
    assert out.laundering_suspected == (expected is AuditVerdict.INTEGRITY_CONFLICT)


def test_unverified_manifest_lowers_confidence():
    valid = audit(C2PAResult(V, AI), WatermarkResult(D, "t"))
    unverified = audit(C2PAResult(U, AI), WatermarkResult(D, "t"))
    assert unverified.confidence < valid.confidence


class _FixedDetector:
    name = "fixed"

    def __init__(self, pattern):
        self.pattern = iter(pattern)

    def detect_frame(self, rgb):
        return next(self.pattern)


@pytest.mark.parametrize("pattern,expected", [
    ([True] * 10, WatermarkStatus.DETECTED),
    ([True] * 5 + [False] * 5, WatermarkStatus.PARTIAL),
    ([True] + [False] * 9, WatermarkStatus.NOT_DETECTED),
    ([None] * 10, WatermarkStatus.UNAVAILABLE),
])
def test_video_detection_rate_bands(pattern, expected):
    r = scan_frames(_FixedDetector(pattern), [None] * len(pattern), is_video=True)
    assert r.status is expected


def test_unavailable_differs_from_not_detected():
    assert scan_frames(UnavailableDetector(), [None], is_video=False).status is NA


def test_container_scan():
    assert scan_container(b"random bytes c2pa").state is ManifestState.NONE
    blob = b"...jumb...c2pa...http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
    r = scan_container(blob)
    assert r.state is ManifestState.UNVERIFIED and r.claim is AI
    assert scan_container(b"jumb c2pa.claim digitalCapture").claim is HUMAN


def test_plain_image_is_no_evidence_not_real():
    r = ProvenanceAxis().analyze(bundle_from_image(png_bytes(natural(64))))
    assert r.status is AxisStatus.NO_EVIDENCE and r.score is None
    assert "진본 증명 아님" in r.gate_reason
