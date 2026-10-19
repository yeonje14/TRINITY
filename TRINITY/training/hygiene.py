"""학습 데이터 위생 — 지름길 학습 차단 (README §7).

탐지기는 항상 가장 값싼 상관관계를 암기한다. 학습 전 데이터셋 매니페스트로 네 가지를 점검한다.

| # | 지름길                   | 점검                                      | 차단책                         |
|---|--------------------------|-------------------------------------------|--------------------------------|
| 1 | 고주파 풍부 = 가짜       | 클래스별 JPEG 품질 분포 차이              | align_compression()            |
| 2 | 워터마크 = 가짜          | 클래스별 워터마크 보유율 차이             | 양 클래스 워터마크 탈상관      |
| 3 | 특정 피사체 = 가짜       | 클래스별 피사체 카테고리 분포 (JS 발산)   | 제3축 SVD 의미 감산            |
| 4 | 특정 촬영 스타일 = 진짜  | 수집 출처가 한 클래스에만 존재하는지      | 동일 출처 수집 / 출처 분포 정렬|

매니페스트 레코드 형식:
    {"label": "real" | "fake", "source": str, "jpeg_quality": int | None,
     "has_watermark": bool, "category": str}
"""
from __future__ import annotations

import io
from collections import Counter
from dataclasses import dataclass, field

import numpy as np
from PIL import Image

# 경고 기준
MAX_QUALITY_GAP = 5.0       # 클래스 간 평균 JPEG 품질 차
MAX_WATERMARK_GAP = 0.1     # 클래스 간 워터마크 보유율 차
MAX_CATEGORY_JS = 0.1       # 카테고리 분포 JS 발산 (bits)
MAX_EXCLUSIVE_SOURCE = 0.2  # 한 클래스에만 있는 출처의 샘플 비율


@dataclass
class CheckResult:
    key: str
    passed: bool
    value: float | None
    message: str


@dataclass
class HygieneReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def summary(self) -> str:
        lines = [f"{'✅' if c.passed else '⚠️'} [{c.key}] {c.message}" for c in self.checks]
        return "\n".join(lines)


def _split(records: list[dict]) -> tuple[list[dict], list[dict]]:
    return ([r for r in records if r["label"] == "real"],
            [r for r in records if r["label"] == "fake"])


def _js_divergence(a: Counter, b: Counter) -> float:
    keys = sorted(set(a) | set(b))
    p = np.array([a[k] for k in keys], float)
    q = np.array([b[k] for k in keys], float)
    p, q = p / p.sum(), q / q.sum()
    m = (p + q) / 2

    def kl(x, y):
        nz = x > 0
        return float(np.sum(x[nz] * np.log2(x[nz] / y[nz])))

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def check_compression(real: list[dict], fake: list[dict]) -> CheckResult:
    def q(rs):  # 원시(무압축) 출력은 품질 100으로 본다
        return np.mean([r.get("jpeg_quality") or 100 for r in rs])

    gap = abs(q(real) - q(fake))
    return CheckResult("1.compression", gap <= MAX_QUALITY_GAP, float(gap),
                       f"클래스 간 평균 JPEG 품질 차 {gap:.1f} (기준 ≤{MAX_QUALITY_GAP})")


def check_watermark(real: list[dict], fake: list[dict]) -> CheckResult:
    def rate(rs):
        return np.mean([bool(r.get("has_watermark")) for r in rs])

    gap = abs(rate(fake) - rate(real))
    return CheckResult("2.watermark", gap <= MAX_WATERMARK_GAP, float(gap),
                       f"클래스 간 워터마크 보유율 차 {gap:.2f} (기준 ≤{MAX_WATERMARK_GAP})")


def check_semantics(real: list[dict], fake: list[dict]) -> CheckResult:
    js = _js_divergence(Counter(r.get("category", "?") for r in real),
                        Counter(r.get("category", "?") for r in fake))
    return CheckResult("3.semantic", js <= MAX_CATEGORY_JS, js,
                       f"피사체 카테고리 분포 JS 발산 {js:.3f} (기준 ≤{MAX_CATEGORY_JS})")


def check_domain(real: list[dict], fake: list[dict]) -> CheckResult:
    real_src = {r["source"] for r in real}
    fake_src = {r["source"] for r in fake}
    shared = real_src & fake_src
    exclusive = [r for r in real + fake if r["source"] not in shared]
    ratio = len(exclusive) / max(len(real) + len(fake), 1)
    return CheckResult("4.domain", ratio <= MAX_EXCLUSIVE_SOURCE, ratio,
                       f"한 클래스에만 있는 출처의 샘플 비율 {ratio:.2f} (기준 ≤{MAX_EXCLUSIVE_SOURCE})")


def run_checks(records: list[dict]) -> HygieneReport:
    real, fake = _split(records)
    if not real or not fake:
        raise ValueError("real/fake 두 클래스가 모두 필요합니다")
    return HygieneReport([check_compression(real, fake), check_watermark(real, fake),
                          check_semantics(real, fake), check_domain(real, fake)])


def align_compression(image: np.ndarray, rng: np.random.Generator,
                      quality_range: tuple[int, int] = (70, 95)) -> np.ndarray:
    """DDA식 압축 정렬: 진짜·가짜 모두 같은 분포의 JPEG 재압축을 거치게 한다."""
    buf = io.BytesIO()
    Image.fromarray(image).save(buf, format="JPEG", quality=int(rng.integers(*quality_range)))
    return np.asarray(Image.open(buf).convert("RGB"))
