"""C2PA 매니페스트 파싱·서명 검증.

공식 라이브러리(c2pa-python)가 있으면 서명까지 검증하고,
없으면 컨테이너 바이트를 스캔해 매니페스트 존재와 주장만 읽는다 (서명 미검증).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ManifestState(str, Enum):
    NONE = "none"                      # 매니페스트 없음
    VALID = "valid"                    # 서명 검증 통과
    INVALID = "invalid"                # 서명·해시 검증 실패 → 변조 의심
    UNVERIFIED = "unverified"          # 존재는 확인했으나 서명 검증 불가 (폴백 스캔)


class ManifestClaim(str, Enum):
    AI_GENERATED = "ai_generated"
    HUMAN = "human"          # 촬영·사람 편집을 주장
    UNKNOWN = "unknown"


# IPTC digitalSourceType 어휘 — C2PA가 생성 여부를 표기하는 표준 방식
_AI_SOURCE_TYPES = (
    b"trainedAlgorithmicMedia",
    b"compositeWithTrainedAlgorithmicMedia",
    b"algorithmicMedia",
)
_HUMAN_SOURCE_TYPES = (
    b"digitalCapture",
    b"negativeFilm",
    b"positiveFilm",
    b"print",
    b"minorHumanEdits",
    b"compositeCapture",
)
_MANIFEST_MARKERS = (b"jumb", b"c2pa.claim", b"c2pa.manifest")


@dataclass
class C2PAResult:
    state: ManifestState
    claim: ManifestClaim = ManifestClaim.UNKNOWN
    generator: str | None = None
    method: str = "none"  # library | container_scan | none
    errors: list[str] = field(default_factory=list)


def classify_claim(blob: bytes) -> ManifestClaim:
    if any(t in blob for t in _AI_SOURCE_TYPES):
        return ManifestClaim.AI_GENERATED
    if any(t in blob for t in _HUMAN_SOURCE_TYPES):
        return ManifestClaim.HUMAN
    return ManifestClaim.UNKNOWN


def scan_container(data: bytes) -> C2PAResult:
    """폴백: JUMBF/C2PA 마커 존재 여부와 digitalSourceType 문자열만 확인."""
    # 'c2pa' 4바이트만으로는 임의 바이너리에서 우연히 맞을 수 있어 JUMBF 박스나 claim 라벨을 함께 요구
    if not (b"c2pa" in data and any(m in data for m in _MANIFEST_MARKERS)):
        return C2PAResult(ManifestState.NONE, method="container_scan")
    return C2PAResult(ManifestState.UNVERIFIED, claim=classify_claim(data),
                      method="container_scan")


def _read_with_library(path: Path) -> C2PAResult | None:
    try:
        import c2pa  # c2pa-python
    except ImportError:
        return None
    try:
        reader = c2pa.Reader(str(path))
        store = json.loads(reader.json())
    except Exception as exc:  # 매니페스트 없음도 예외로 온다
        msg = str(exc)
        if "ManifestNotFound" in msg or "JumbfNotFound" in msg or "no manifest" in msg.lower():
            return C2PAResult(ManifestState.NONE, method="library")
        return C2PAResult(ManifestState.INVALID, method="library", errors=[msg])

    active = store.get("manifests", {}).get(store.get("active_manifest", ""), {})
    blob = json.dumps(active).encode()
    errors = [s.get("code", "") for s in store.get("validation_status", []) or []]
    return C2PAResult(
        ManifestState.INVALID if errors else ManifestState.VALID,
        claim=classify_claim(blob),
        generator=active.get("claim_generator"),
        method="library",
        errors=errors,
    )


def read_manifest(path: Path | None = None, data: bytes | None = None) -> C2PAResult:
    if path is not None:
        result = _read_with_library(path)
        if result is not None:
            return result
        data = data if data is not None else Path(path).read_bytes()
    if data is None:
        return C2PAResult(ManifestState.NONE, errors=["입력 파일 없음"])
    return scan_container(data)
