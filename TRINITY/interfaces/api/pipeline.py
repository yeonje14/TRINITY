"""3축 조립 및 실행 오케스트레이션.

입력 → FrameBundle → 3축 병렬 실행 → (출처 축 내부) 교차 감사 → 동적 가중 융합 → AnalysisResult
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

from core.axis_provenance import ProvenanceAxis
from core.axis_semantic import ReferenceDistribution, SemanticAxis
from core.axis_semantic.encoders import load_encoder
from core.axis_signal import SignalAxis
from core.contracts import Axis, AxisResult, AxisStatus, FrameBundle
from core.ensemble import DynamicEnsemble, EnsembleResult
from preprocessing.ingest import bundle_from_image, bundle_from_video, download_youtube

from .schemas import AnalysisResult, AxisOut, EvidenceOut, SourceInfo

log = logging.getLogger("trinity.pipeline")

Progress = Callable[[float, str], None]


def _noop(_: float, __: str) -> None:
    pass


def _jsonable(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    return x


def default_axes() -> list[Axis]:
    """환경변수로 선택 구성요소를 주입한다.
    TRINITY_SIGNAL_WEIGHTS: 축1-B 가중치(.pt)
    TRINITY_SEMANTIC_ENCODER: 비전 인코더 이름 (예: openai/clip-vit-base-patch32)
    TRINITY_REFERENCE: 참조 분포(.npz) — 인코더와 함께 있어야 분포 편차 활성
    """
    weights = os.getenv("TRINITY_SIGNAL_WEIGHTS")
    encoder = None
    if name := os.getenv("TRINITY_SEMANTIC_ENCODER"):
        encoder = load_encoder(name)
        if encoder is None:
            log.warning("비전 인코더 로드 실패: %s — 분포 편차 비활성", name)
    reference = None
    if ref := os.getenv("TRINITY_REFERENCE"):
        reference = ReferenceDistribution.load(Path(ref))
    return [SignalAxis(Path(weights) if weights else None),
            ProvenanceAxis(),
            SemanticAxis(encoder, reference)]


class TrinityPipeline:
    def __init__(self, axes: list[Axis] | None = None, ensemble: DynamicEnsemble | None = None):
        self.axes = axes if axes is not None else default_axes()
        self.ensemble = ensemble or DynamicEnsemble()
        self._pool = ThreadPoolExecutor(max_workers=len(self.axes) or 1,
                                        thread_name_prefix="trinity-axis")

    def _run_axis(self, axis: Axis, bundle: FrameBundle) -> AxisResult:
        try:
            return axis.analyze(bundle)
        except Exception as exc:
            log.exception("축 실행 실패: %s", axis.name)
            return AxisResult(axis.name, AxisStatus.ERROR, gate_reason=f"실행 오류: {exc}")

    def run(self, bundle: FrameBundle, source: SourceInfo | None = None,
            progress: Progress = _noop) -> AnalysisResult:
        progress(0.5, "analyzing")
        futures = [self._pool.submit(self._run_axis, a, bundle) for a in self.axes]
        results = [f.result() for f in futures]
        progress(0.9, "fusing")
        fused = self.ensemble.fuse(results, bundle.quality)
        return self._to_result(fused, bundle, source or SourceInfo())

    def analyze_image(self, data: bytes, filename: str | None = None) -> AnalysisResult:
        bundle = bundle_from_image(data, filename)
        return self.run(bundle, SourceInfo(filename=filename))

    def analyze_url(self, url: str, progress: Progress = _noop) -> AnalysisResult:
        workdir = Path(tempfile.mkdtemp(prefix="trinity-"))
        try:
            progress(0.05, "downloading")
            path, meta = download_youtube(url, workdir)
            progress(0.3, "preprocessing")
            bundle = bundle_from_video(path, meta)
            return self.run(bundle, SourceInfo(**{k: meta.get(k) for k in SourceInfo.model_fields}),
                            progress)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)  # 원본 영상은 보관하지 않는다

    @staticmethod
    def _to_result(fused: EnsembleResult, bundle: FrameBundle, source: SourceInfo) -> AnalysisResult:
        axes = [
            AxisOut(axis=r.axis, status=r.status, score=r.score, confidence=r.confidence,
                    weight=fused.weights.get(r.axis, 0.0), gate_reason=r.gate_reason,
                    evidence=[EvidenceOut(**e.__dict__) for e in r.evidence],
                    details=_jsonable(r.details))
            for r in fused.axes.values()
        ]
        q = bundle.quality
        return AnalysisResult(
            id=uuid.uuid4().hex, track=bundle.track, risk_level=fused.level,
            score=fused.score, confidence=fused.confidence, axes=axes,
            flags=fused.flags, gates=fused.gates,
            evidence=[EvidenceOut(**e.__dict__) for e in fused.evidence],
            quality={"width": q.width, "height": q.height, "sharpness": q.sharpness,
                     "blockiness": q.blockiness, "low_quality": q.low_quality},
            source=source, created_at=datetime.now(timezone.utc))
