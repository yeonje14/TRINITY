"""합성 테스트 데이터 — 판정 '순서'와 근거 방향 검증용 (절대 성능 아님)."""
from __future__ import annotations

import io

import numpy as np
from PIL import Image


def natural(size: int = 512, seed: int = 0) -> np.ndarray:
    """1/f 진폭 스펙트럼(파워 ~1/f²) 랜덤 위상 + 약한 센서 노이즈 — 자연 영상 통계 근사."""
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    f = np.hypot(fx, fy)
    f[0, 0] = 1.0
    channels = []
    for _ in range(3):
        phase = np.exp(2j * np.pi * rng.random((size, size)))
        img = np.real(np.fft.ifft2(phase / f))
        channels.append(img)
    x = np.stack(channels, -1)
    x = (x - x.min()) / (x.max() - x.min()) * 220 + 15
    x += rng.normal(0, 2.0, x.shape)
    return np.clip(x, 0, 255).astype(np.uint8)


def generated(size: int = 512, seed: int = 0, strength: float = 0.06) -> np.ndarray:
    """×2 업샘플링 + 전치 합성곱 체커보드 근사 — 나이퀴스트 격자 위치에 주기 흔적."""
    small = natural(size // 2, seed)
    up = small.repeat(2, 0).repeat(2, 1).astype(np.float32)
    yy, xx = np.mgrid[:size, :size]
    checker = 1 + strength * (((yy % 2) + (xx % 2)) % 2 * 2 - 1)
    return np.clip(up * checker[..., None], 0, 255).astype(np.uint8)


def jpeg(img: np.ndarray, quality: int = 70) -> np.ndarray:
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="JPEG", quality=quality)
    return np.asarray(Image.open(buf).convert("RGB"))


def interpolated(size: int = 512, seed: int = 0) -> np.ndarray:
    small = Image.fromarray(natural(size // 2, seed))
    return np.asarray(small.resize((size, size), Image.BILINEAR))


def png_bytes(img: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="PNG")
    return buf.getvalue()
