"""FFT 스펙트럼 분석 — 방사 프로파일, 멱법칙 이탈, 격자 피크 검출, 스펙트럼 잔차 맵.

판별은 고주파 '총량'이 아니라 '주기적 격자 구조의 위치'로 한다.
업샘플링 흔적은 정규화 주파수 1/2, 1/4 등 특정 위치에 규칙적으로 서지만,
센서 노이즈·렌즈 회절은 비주기적·광대역이다.

주파수 좌표는 모두 cycles/pixel 단위이며 나이퀴스트는 0.5.
FFT는 CPU(numpy)에서 수행한다 — MPS의 torch.fft 제약 회피 (README §8).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_EPS = 1e-10

# 업샘플링 배율 2·4가 남기는 주기 위치 (강한 근거)
UPSAMPLE_POSITIONS = (0.25, 0.5)
# 8x8 블록(JPEG 등)이 남기는 위치 중 업샘플링 위치를 뺀 나머지 (약한 근거)
BLOCK_POSITIONS = (0.125, 0.375)


@dataclass(frozen=True)
class GridPeak:
    u: float
    v: float
    z: float           # 방사 추세 대비 강도 (robust z-score)
    on_upsample_grid: bool
    on_block_grid: bool


@dataclass(frozen=True)
class SpectrumFeatures:
    powerlaw_slope: float  # 자연 영상은 대략 -2 근처
    hf_excess: float       # 고대역에서 멱법칙 예측 대비 초과량 (log10)
    grid_strength: float   # 위치 게이팅된 격자 피크 강도 합
    peaks: tuple[GridPeak, ...]

    @property
    def on_grid_count(self) -> int:
        return sum(p.on_upsample_grid or p.on_block_grid for p in self.peaks)

    @property
    def off_grid_count(self) -> int:
        return len(self.peaks) - self.on_grid_count


def _freq_grid(h: int, w: int) -> tuple[np.ndarray, np.ndarray]:
    v = np.fft.fftshift(np.fft.fftfreq(h))[:, None]
    u = np.fft.fftshift(np.fft.fftfreq(w))[None, :]
    return np.broadcast_to(u, (h, w)), np.broadcast_to(v, (h, w))


def log_power_spectrum(gray: np.ndarray) -> np.ndarray:
    """Hann 창을 씌운 2D 로그 파워 스펙트럼 (중앙이 DC)."""
    g = gray.astype(np.float64)
    g = g - g.mean()
    win = np.outer(np.hanning(g.shape[0]), np.hanning(g.shape[1]))
    spec = np.fft.fftshift(np.fft.fft2(g * win))
    return np.log10(np.abs(spec) ** 2 + _EPS)


def radial_profile(log_power: np.ndarray, n_bins: int = 64) -> tuple[np.ndarray, np.ndarray]:
    """방위각 평균. (bin 중심 주파수, 평균 로그 파워)를 반환."""
    u, v = _freq_grid(*log_power.shape)
    r = np.hypot(u, v)
    edges = np.linspace(0.0, 0.5, n_bins + 1)
    idx = np.clip(np.digitize(r.ravel(), edges) - 1, 0, n_bins - 1)
    sums = np.bincount(idx, weights=log_power.ravel(), minlength=n_bins)
    counts = np.bincount(idx, minlength=n_bins)
    profile = sums / np.maximum(counts, 1)
    centers = (edges[:-1] + edges[1:]) / 2
    return centers, profile


def powerlaw_fit(freqs: np.ndarray, profile: np.ndarray,
                 fit_band: tuple[float, float] = (0.04, 0.2),
                 test_band: tuple[float, float] = (0.25, 0.5)) -> tuple[float, float]:
    """중대역에서 log-log 직선을 맞추고, 고대역 초과량을 잰다. (slope, hf_excess)"""
    fit = (freqs >= fit_band[0]) & (freqs <= fit_band[1])
    test = (freqs >= test_band[0]) & (freqs <= test_band[1])
    if fit.sum() < 3 or test.sum() < 1:
        return 0.0, 0.0
    slope, intercept = np.polyfit(np.log10(freqs[fit]), profile[fit], 1)
    predicted = slope * np.log10(freqs[test]) + intercept
    return float(slope), float(np.mean(profile[test] - predicted))


def _near_any(x: np.ndarray, positions: tuple[float, ...], tol: float) -> np.ndarray:
    ax = np.abs(x)
    hit = ax <= tol  # 0 (축 위)도 격자의 일부로 본다
    for p in positions:
        hit |= np.abs(ax - p) <= tol
    return hit


def detect_grid_peaks(log_power: np.ndarray, z_thresh: float = 6.0,
                      min_radius: float = 0.06, max_peaks: int = 32) -> list[GridPeak]:
    """방사 추세를 뺀 잔차에서 국소 최대 피크를 찾고, 위치로 분류한다."""
    h, w = log_power.shape
    u, v = _freq_grid(h, w)
    r = np.hypot(u, v)

    freqs, profile = radial_profile(log_power)
    trend = np.interp(r, freqs, profile)
    resid = log_power - trend

    valid = r >= min_radius
    vals = resid[valid]
    med = np.median(vals)
    mad = np.median(np.abs(vals - med)) * 1.4826 + _EPS
    z = (resid - med) / mad

    # 3x3 국소 최대
    padded = np.pad(z, 1, mode="constant", constant_values=-np.inf)
    neigh = np.max(np.stack([padded[dy:dy + h, dx:dx + w]
                             for dy in range(3) for dx in range(3)
                             if not (dy == 1 and dx == 1)]), axis=0)
    mask = valid & (z >= z_thresh) & (z > neigh)

    tol = 1.5 / min(h, w)
    ys, xs = np.nonzero(mask)
    order = np.argsort(-z[ys, xs])[:max_peaks]
    peaks = []
    for i in order:
        y, x = ys[i], xs[i]
        pu, pv = float(u[y, x]), float(v[y, x])
        up = bool(_near_any(np.array([pu, pv]), UPSAMPLE_POSITIONS, tol).all())
        blk = (not up) and bool(_near_any(np.array([pu, pv]),
                                          UPSAMPLE_POSITIONS + BLOCK_POSITIONS, tol).all())
        peaks.append(GridPeak(pu, pv, float(z[y, x]), up, blk))
    return peaks


def grid_strength(peaks: list[GridPeak], z_cap: float = 30.0) -> float:
    """강도 × 위치 게이팅. 격자 밖 피크는 0, 블록 격자는 절반만 반영."""
    total = 0.0
    for p in peaks:
        if p.on_upsample_grid:
            total += min(p.z, z_cap)
        elif p.on_block_grid:
            total += 0.5 * min(p.z, z_cap)
    return total


def analyze_patch(gray: np.ndarray) -> SpectrumFeatures:
    lp = log_power_spectrum(gray)
    freqs, profile = radial_profile(lp)
    slope, excess = powerlaw_fit(freqs, profile)
    peaks = detect_grid_peaks(lp)
    return SpectrumFeatures(slope, excess, grid_strength(peaks), tuple(peaks))


def spectral_residual_map(gray: np.ndarray, cutoff: float = 0.25) -> np.ndarray:
    """고대역 통과 후 iFFT로 재구성한 잔차 맵 (설명용 히트맵 원천). 0~1 정규화."""
    g = gray.astype(np.float64) - gray.mean()
    spec = np.fft.fftshift(np.fft.fft2(g))
    u, v = _freq_grid(*g.shape)
    spec[np.hypot(u, v) < cutoff] = 0
    resid = np.abs(np.fft.ifft2(np.fft.ifftshift(spec)))
    return resid / (resid.max() + _EPS)
