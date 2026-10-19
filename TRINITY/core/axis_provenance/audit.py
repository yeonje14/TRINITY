"""무결성 충돌 교차 감사 (cross-layer audit) ★프로젝트 기여점.

C2PA 검증(메타데이터 서명)과 워터마크 검출(픽셀 신호)은 서로를 참조하지 않는 독립 절차라
"사람이 편집함"을 주장하는 유효 매니페스트와 "AI 생성" 워터마크가 한 파일에 공존할 수 있다
— '인증된 가짜(Authenticated Fakes)'. 두 계층을 충돌 매트릭스로 교차해 모순을 세탁 의심으로 승격한다.

영상 확장: 컨테이너당 매니페스트 1개 : 프레임마다 워터마크라는 비대칭 때문에
프레임별 검출률이 20~80%면 '부분 합성 의심'이라는, 이미지에 없는 상태가 생긴다.

| C2PA 주장       | 워터마크        | 판정                          |
|-----------------|-----------------|-------------------------------|
| 서명 무효       | —               | TAMPER_SUSPECTED              |
| AI 생성         | 검출            | CONSISTENT_AI (가장 강한 증거)|
| AI 생성         | 미검출          | WATERMARK_REMOVAL_SUSPECTED   |
| AI 생성         | 미가용          | SINGLE_LAYER_MANIFEST         |
| 사람 편집       | 검출/부분       | INTEGRITY_CONFLICT ★          |
| 사람 편집       | 미검출/미가용   | NO_INFORMATION                |
| 없음            | 검출            | SINGLE_LAYER_WATERMARK        |
| 없음 / AI 생성  | 부분 (영상)     | PARTIAL_SYNTHESIS             |
| 없음            | 미검출/미가용   | NO_INFORMATION (진본 증명 아님)|
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .c2pa import C2PAResult, ManifestClaim, ManifestState
from .synthid import WatermarkResult, WatermarkStatus


class AuditVerdict(str, Enum):
    TAMPER_SUSPECTED = "tamper_suspected"
    CONSISTENT_AI = "consistent_ai"
    WATERMARK_REMOVAL_SUSPECTED = "watermark_removal_suspected"
    SINGLE_LAYER_MANIFEST = "single_layer_manifest"
    INTEGRITY_CONFLICT = "integrity_conflict"
    SINGLE_LAYER_WATERMARK = "single_layer_watermark"
    PARTIAL_SYNTHESIS = "partial_synthesis"
    NO_INFORMATION = "no_information"


# 판정별 (AI 점수, 신뢰도, 메시지). 점수는 앙상블에서 재보정 대상.
_TABLE: dict[AuditVerdict, tuple[float | None, float, str]] = {
    AuditVerdict.TAMPER_SUSPECTED: (0.65, 0.5, "C2PA 서명·해시 검증 실패 — 변조 의심"),
    AuditVerdict.CONSISTENT_AI: (0.95, 0.9, "매니페스트와 워터마크가 모두 AI 생성을 가리킴"),
    AuditVerdict.WATERMARK_REMOVAL_SUSPECTED: (
        0.85, 0.7, "매니페스트는 AI 생성을 주장하나 워터마크 미검출 — 워터마크 제거 의심"),
    AuditVerdict.SINGLE_LAYER_MANIFEST: (
        0.85, 0.65, "매니페스트가 AI 생성을 주장 (워터마크 탐지기 미연결)"),
    AuditVerdict.INTEGRITY_CONFLICT: (
        0.9, 0.75, "매니페스트는 사람 편집을 주장하나 AI 워터마크가 검출됨 — 출처 세탁 의심"),
    AuditVerdict.SINGLE_LAYER_WATERMARK: (0.85, 0.65, "AI 워터마크 검출 (매니페스트 없음)"),
    AuditVerdict.PARTIAL_SYNTHESIS: (
        0.8, 0.6, "일부 프레임에서만 워터마크 검출 — 생성 클립과 실촬영 구간 혼재 의심"),
    AuditVerdict.NO_INFORMATION: (None, 0.0, "출처 신호 없음 — 진본을 증명하지 않음"),
}

UNVERIFIED_PENALTY = 0.8  # 서명 검증 없이 컨테이너 스캔으로만 읽은 매니페스트


@dataclass
class AuditOutcome:
    verdict: AuditVerdict
    score: float | None
    confidence: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def positive(self) -> bool:
        return self.score is not None

    @property
    def laundering_suspected(self) -> bool:
        return self.verdict is AuditVerdict.INTEGRITY_CONFLICT


def _decide(manifest: C2PAResult, wm: WatermarkStatus) -> AuditVerdict:
    if manifest.state is ManifestState.INVALID:
        return AuditVerdict.TAMPER_SUSPECTED

    has_manifest = manifest.state in (ManifestState.VALID, ManifestState.UNVERIFIED)
    claim = manifest.claim if has_manifest else ManifestClaim.UNKNOWN

    if claim is ManifestClaim.HUMAN:
        if wm in (WatermarkStatus.DETECTED, WatermarkStatus.PARTIAL):
            return AuditVerdict.INTEGRITY_CONFLICT
        return AuditVerdict.NO_INFORMATION

    if wm is WatermarkStatus.PARTIAL:
        return AuditVerdict.PARTIAL_SYNTHESIS

    if claim is ManifestClaim.AI_GENERATED:
        return {
            WatermarkStatus.DETECTED: AuditVerdict.CONSISTENT_AI,
            WatermarkStatus.NOT_DETECTED: AuditVerdict.WATERMARK_REMOVAL_SUSPECTED,
        }.get(wm, AuditVerdict.SINGLE_LAYER_MANIFEST)

    if wm is WatermarkStatus.DETECTED:
        return AuditVerdict.SINGLE_LAYER_WATERMARK
    return AuditVerdict.NO_INFORMATION


def audit(manifest: C2PAResult, watermark: WatermarkResult) -> AuditOutcome:
    verdict = _decide(manifest, watermark.status)
    score, confidence, message = _TABLE[verdict]
    if manifest.state is ManifestState.UNVERIFIED and verdict not in (
            AuditVerdict.SINGLE_LAYER_WATERMARK, AuditVerdict.NO_INFORMATION):
        confidence *= UNVERIFIED_PENALTY
    if verdict is AuditVerdict.INTEGRITY_CONFLICT and watermark.status is WatermarkStatus.PARTIAL:
        message += " (부분 합성 동반)"
    return AuditOutcome(
        verdict, score, confidence, message,
        details={
            "manifest_state": manifest.state.value,
            "manifest_claim": manifest.claim.value,
            "manifest_method": manifest.method,
            "generator": manifest.generator,
            "watermark_status": watermark.status.value,
            "watermark_detector": watermark.detector,
            "watermark_rate": watermark.detection_rate,
        },
    )
