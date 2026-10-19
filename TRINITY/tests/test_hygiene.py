import numpy as np

from training.hygiene import align_compression, run_checks


def _rec(label, source="flickr", q=85, wm=False, cat="street"):
    return {"label": label, "source": source, "jpeg_quality": q, "has_watermark": wm, "category": cat}


def test_clean_dataset_passes():
    recs = [_rec("real") for _ in range(50)] + [_rec("fake") for _ in range(50)]
    assert run_checks(recs).passed


def test_each_shortcut_is_flagged():
    recs = ([_rec("real", source="flickr", q=75, cat="street") for _ in range(50)]
            + [_rec("fake", source="midjourney", q=None, wm=True, cat="portrait") for _ in range(50)])
    report = run_checks(recs)
    failed = {c.key for c in report.checks if not c.passed}
    assert failed == {"1.compression", "2.watermark", "3.semantic", "4.domain"}
    assert "⚠️" in report.summary()


def test_align_compression_roundtrip():
    img = np.random.default_rng(0).integers(0, 255, (64, 64, 3), dtype=np.uint8)
    out = align_compression(img, np.random.default_rng(0))
    assert out.shape == img.shape and out.dtype == np.uint8
