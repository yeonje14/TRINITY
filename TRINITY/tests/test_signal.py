import numpy as np
import pytest

from core.axis_signal import SignalAxis
from core.axis_signal.freq_masking import apply_frequency_mask
from core.axis_signal.spectrum import analyze_patch, spectral_residual_map
from core.contracts import AxisStatus
from preprocessing.ingest import bundle_from_image
from synthetic import generated, interpolated, jpeg, natural, png_bytes


def _score(img):
    return SignalAxis().analyze(bundle_from_image(png_bytes(img)))


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_generated_scores_above_all_real_variants(seed):
    gen = _score(generated(seed=seed)).score
    for real in (natural(seed=seed), jpeg(natural(seed=seed)), interpolated(seed=seed)):
        assert gen > _score(real).score + 0.3


def test_upsampling_peaks_land_on_grid():
    gray = generated()[:256, :256].mean(-1)
    f = analyze_patch(gray)
    assert f.on_grid_count > 0
    assert all(p.on_upsample_grid for p in f.peaks if p.z > 10)


def test_natural_has_no_grid_peaks_and_powerlaw_slope():
    f = analyze_patch(natural()[:256, :256].mean(-1))
    assert f.on_grid_count == 0
    assert -3.0 < f.powerlaw_slope < -1.0


def test_low_quality_halves_confidence():
    blurred = interpolated()
    r = _score(blurred)
    assert r.status is AxisStatus.OK
    assert any(e.code == "signal.low_quality" for e in r.evidence)


def test_residual_map_normalized():
    m = spectral_residual_map(natural()[:128, :128].mean(-1))
    assert m.shape == (128, 128) and 0 <= m.min() and m.max() == pytest.approx(1.0)


def test_frequency_mask_preserves_shape_and_dtype():
    img = natural(128)
    out = apply_frequency_mask(img, np.random.default_rng(0))
    assert out.shape == img.shape and out.dtype == img.dtype
    assert not np.array_equal(out, img)
