import shutil
import subprocess

import numpy as np
import pytest

from core.contracts import Track
from preprocessing.ingest import (PATCH_SIZE, blockiness, bundle_from_image, bundle_from_video,
                                  select_patches)
from synthetic import interpolated, jpeg, natural, png_bytes


def test_patches_keep_native_scale():
    img = natural(600)
    patches = select_patches(img)
    assert len(patches) == 4
    assert all(p.shape == (PATCH_SIZE, PATCH_SIZE, 3) for p in patches)


def test_patches_skip_flat_regions():
    img = natural(512)
    img[:256, :256] = 128  # 평탄한 사분면
    patches = select_patches(img, k=3)
    assert not any(np.all(p == 128) for p in patches)


def test_small_image_uses_whole_frame():
    (p,) = select_patches(natural(100))
    assert p.shape[:2] == (100, 100)


def test_image_bundle_and_quality():
    b = bundle_from_image(png_bytes(natural(512)), "x.png")
    assert b.track is Track.IMAGE and b.raw_bytes and len(b.frames) == 1
    assert not b.quality.low_quality
    assert bundle_from_image(png_bytes(interpolated())).quality.low_quality


def test_blockiness_detects_jpeg():
    g = lambda im: im.astype(np.float32).mean(-1)
    assert blockiness(g(jpeg(natural(), 15))) > blockiness(g(natural())) + 0.2


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg 필요")
def test_video_three_point_biopsy(tmp_path):
    path = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                    "testsrc2=size=640x480:rate=30:duration=4",
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    b = bundle_from_video(path, {"channel_id": "UC123"})
    segs = b.segments()
    assert set(segs) == {"start", "middle", "end"}
    assert all(len(v) == 8 for v in segs.values())
    assert b.frames[0].pixels.shape == (480, 640, 3)  # 리사이즈 없음
    assert b.metadata["channel_id"] == "UC123"
    assert segs["start"][0].timestamp < segs["middle"][0].timestamp < segs["end"][0].timestamp
