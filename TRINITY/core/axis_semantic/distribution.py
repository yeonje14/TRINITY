"""분포 편차 + SVD 의미 감산.

실제 이미지 특징 분포로부터의 마할라노비스 편차를 재되, 피사체 의미가 판별 기준이 되는
'의미론적 지름길'을 막기 위해 의미 우세 부분공간(상위 특이벡터)을 먼저 감산한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


def semantic_subspace(features: np.ndarray, rank: int) -> np.ndarray:
    """중심화한 특징 행렬의 상위 rank개 우특이벡터 (rank, D)."""
    centered = features - features.mean(0, keepdims=True)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    return vt[:rank]


def subtract_subspace(features: np.ndarray, basis: np.ndarray) -> np.ndarray:
    if basis.size == 0:
        return features
    return features - (features @ basis.T) @ basis


@dataclass
class ReferenceDistribution:
    mean: np.ndarray
    precision: np.ndarray
    basis: np.ndarray           # 감산할 의미 부분공간
    threshold: float            # 실제 분포 거리의 상위 분위수 (보정 기준점)
    scale: float                # 거리 분산 — 점수 경사

    @classmethod
    def fit(cls, real_features: np.ndarray, semantic_rank: int = 8,
            shrinkage: float = 0.1, quantile: float = 0.95) -> "ReferenceDistribution":
        x = np.asarray(real_features, dtype=np.float64)
        if x.shape[0] < 2:
            raise ValueError("참조 분포에는 최소 2개 이상의 실제 이미지 특징이 필요합니다")
        basis = semantic_subspace(x, min(semantic_rank, x.shape[1] - 1, x.shape[0] - 1))
        r = subtract_subspace(x, basis)
        mean = r.mean(0)
        cov = np.cov(r, rowvar=False)
        # 샘플 수 < 차원이면 공분산이 특이 — 대각 수축으로 안정화
        cov = (1 - shrinkage) * cov + shrinkage * np.eye(cov.shape[0]) * np.trace(cov) / cov.shape[0]
        precision = np.linalg.pinv(cov)
        ref = cls(mean, precision, basis, threshold=0.0, scale=1.0)
        d = ref.distance(x)
        ref.threshold = float(np.quantile(d, quantile))
        ref.scale = float(np.std(d) + 1e-6)
        return ref

    def distance(self, features: np.ndarray) -> np.ndarray:
        r = subtract_subspace(np.atleast_2d(features).astype(np.float64), self.basis) - self.mean
        return np.sqrt(np.maximum(np.einsum("nd,de,ne->n", r, self.precision, r), 0.0))

    def score(self, features: np.ndarray) -> np.ndarray:
        """보정 기준점을 넘을수록 1에 가까워지는 0~1 점수."""
        d = self.distance(features)
        return 1.0 / (1.0 + np.exp(-(d - self.threshold) / self.scale))

    def save(self, path: Path) -> None:
        np.savez(path, mean=self.mean, precision=self.precision, basis=self.basis,
                 threshold=self.threshold, scale=self.scale)

    @classmethod
    def load(cls, path: Path) -> "ReferenceDistribution":
        z = np.load(path)
        return cls(z["mean"], z["precision"], z["basis"],
                   float(z["threshold"]), float(z["scale"]))
