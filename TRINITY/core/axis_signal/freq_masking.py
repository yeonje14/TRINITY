"""주파수 도메인 마스킹 증강 — 학습 시 특정 대역 과적합 방지.

임의의 링(방사 대역)이나 쐐기(방위각 구간)를 지운 뒤 역변환한다.
제1축 B(하이브리드 어텐션) 학습 루프에서 입력 증강으로 사용한다.
"""
from __future__ import annotations

import numpy as np


def random_band_mask(shape: tuple[int, int], rng: np.random.Generator,
                     max_bands: int = 2, max_width: float = 0.08,
                     wedge_prob: float = 0.3) -> np.ndarray:
    """1(유지)/0(제거) 마스크. 중앙이 DC인 fftshift 좌표계."""
    h, w = shape
    v = np.fft.fftshift(np.fft.fftfreq(h))[:, None]
    u = np.fft.fftshift(np.fft.fftfreq(w))[None, :]
    r = np.hypot(u, v)
    mask = np.ones(shape, dtype=np.float32)

    for _ in range(rng.integers(1, max_bands + 1)):
        lo = rng.uniform(0.05, 0.5 - max_width)
        mask[(r >= lo) & (r < lo + rng.uniform(0.01, max_width))] = 0

    if rng.random() < wedge_prob:
        # 각도를 π로 접어 반대편 쐐기도 함께 지운다 — 켤레 대칭 유지
        theta = np.mod(np.arctan2(v, u), np.pi)
        start = rng.uniform(0, np.pi)
        span = rng.uniform(np.pi / 16, np.pi / 6)
        wedge = np.mod(theta - start, np.pi) < span
        mask[wedge & (r > 0.02)] = 0

    mask[r < 0.02] = 1  # DC 근처는 항상 보존
    return mask


def apply_frequency_mask(image: np.ndarray, rng: np.random.Generator | None = None,
                         **kwargs) -> np.ndarray:
    """(H, W) 또는 (H, W, C) float/uint8 이미지에 마스크를 적용. 입력과 같은 dtype 반환."""
    rng = rng or np.random.default_rng()
    x = image.astype(np.float64)
    squeeze = x.ndim == 2
    if squeeze:
        x = x[..., None]
    mask = random_band_mask(x.shape[:2], rng, **kwargs)
    out = np.empty_like(x)
    for c in range(x.shape[2]):
        spec = np.fft.fftshift(np.fft.fft2(x[..., c])) * mask
        out[..., c] = np.real(np.fft.ifft2(np.fft.ifftshift(spec)))
    if squeeze:
        out = out[..., 0]
    if np.issubdtype(image.dtype, np.integer):
        out = np.clip(np.rint(out), 0, 255)
    return out.astype(image.dtype)
