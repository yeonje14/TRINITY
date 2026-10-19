import numpy as np

from core.axis_semantic import SemanticAxis
from core.axis_semantic.consistency import analyze_segments
from core.axis_semantic.distribution import ReferenceDistribution
from core.contracts import AxisStatus, Frame, FrameBundle, QualityMetrics, Track
from synthetic import natural

Q = QualityMetrics(256, 256, 500.0, 1.0, False)


def _clip(segment, frames):
    return [Frame(pixels=f, index=i, segment=segment) for i, f in enumerate(frames)]


def _smooth_motion(n=8, seed=0):
    base = natural(320, seed)
    return [base[i * 2:i * 2 + 256, i * 2:i * 2 + 256] for i in range(n)]


def _flicker(n=8, seed=0):
    rng = np.random.default_rng(seed)
    base = natural(256, seed).astype(np.float32)
    out = []
    for i in range(n):
        # 장면 전환으로 오인되지 않을 정도의 깜빡임 + 불규칙 움직임
        shift = int(rng.integers(-6, 7))
        f = np.roll(base, shift, axis=1) * rng.uniform(0.95, 1.05)
        f += rng.normal(0, 8 * (i % 2), f.shape)
        out.append(np.clip(f, 0, 255).astype(np.uint8))
    return out


def test_flicker_scores_higher_than_smooth_motion():
    smooth = analyze_segments({"start": _clip("start", _smooth_motion())})
    flick = analyze_segments({"start": _clip("start", _flicker())})
    assert smooth.pairs == flick.pairs == 7
    assert flick.score > smooth.score


def test_scene_cut_excluded_and_lowers_confidence():
    frames = _smooth_motion(4) + [np.zeros((256, 256, 3), np.uint8)] * 4
    rep = analyze_segments({"start": _clip("start", frames)})
    assert rep.cuts == 1 and rep.pairs == 6


def test_distribution_outlier_scores_higher():
    rng = np.random.default_rng(0)
    real = rng.normal(0, 1, (200, 32))
    ref = ReferenceDistribution.fit(real, semantic_rank=4)
    inlier = rng.normal(0, 1, (20, 32))
    outlier = rng.normal(0, 1, (20, 32)) + 3.0
    assert ref.score(outlier).mean() > ref.score(inlier).mean() + 0.3


def test_semantic_subtraction_ignores_dominant_axis():
    rng = np.random.default_rng(1)
    real = rng.normal(0, 0.1, (200, 16))
    real[:, 0] += rng.normal(0, 5, 200)  # 피사체 의미가 지배하는 축
    ref = ReferenceDistribution.fit(real, semantic_rank=1)
    shifted = rng.normal(0, 0.1, (20, 16))
    shifted[:, 0] += 15  # 의미 축으로만 이동 → 감산되어 무시돼야 함
    assert ref.score(shifted).mean() < 0.8


def test_save_load_roundtrip(tmp_path):
    ref = ReferenceDistribution.fit(np.random.default_rng(0).normal(size=(50, 8)), 2)
    ref.save(tmp_path / "ref.npz")
    loaded = ReferenceDistribution.load(tmp_path / "ref.npz")
    x = np.ones((3, 8))
    np.testing.assert_allclose(loaded.score(x), ref.score(x))


def test_image_without_encoder_is_unavailable():
    b = FrameBundle(Track.IMAGE, [Frame(natural(64))], Q)
    r = SemanticAxis().analyze(b)
    assert r.status is AxisStatus.UNAVAILABLE and "인코더" in r.gate_reason


def test_video_without_encoder_uses_consistency():
    b = FrameBundle(Track.VIDEO, _clip("start", _smooth_motion()), Q)
    r = SemanticAxis().analyze(b)
    assert r.status is AxisStatus.OK and "consistency" in r.details
