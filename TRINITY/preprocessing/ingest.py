"""투트랙 입력 어댑터 — 이미지·영상을 동일한 FrameBundle로 만든다.

- 3-Point Biopsy: 영상 전/중/후 구간에서 짧은 연속 프레임 묶음을 샘플링
  (구간 간 다양성 + 구간 내 연속성 — 제3축 시공간 분석에 필요)
- Native-Scale 원칙: 강제 리사이즈 금지. 고주파 위조 흔적 보존을 위해 원본 해상도 패치를 잘라 쓴다.
- 분산 기반 패치 선택: 평탄한 영역(하늘·벽)은 스펙트럼 정보가 없어 제외
"""
from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from core.contracts import Frame, FrameBundle, QualityMetrics, Track

PATCH_SIZE = 256
PATCHES_PER_FRAME = 4
BIOPSY_POINTS = {"start": 0.1, "middle": 0.5, "end": 0.9}
CLIP_LEN = 8          # 구간당 연속 프레임 수
PATCH_EVERY = 4       # 구간 내 몇 프레임마다 패치를 뽑을지

# 저화질 판정 기준 (재보정 대상)
MIN_SIDE = 360
MIN_SHARPNESS = 40.0
MAX_BLOCKINESS = 1.6


# ---------- 공통 ----------

def _gray(rgb: np.ndarray) -> np.ndarray:
    p = rgb.astype(np.float32)
    return 0.299 * p[..., 0] + 0.587 * p[..., 1] + 0.114 * p[..., 2]


def select_patches(rgb: np.ndarray, size: int = PATCH_SIZE,
                   k: int = PATCHES_PER_FRAME) -> tuple[np.ndarray, ...]:
    """겹치지 않는 size×size 타일 중 밝기 분산 상위 k개. 리사이즈하지 않는다."""
    h, w = rgb.shape[:2]
    if h < size or w < size:
        return (rgb[: h - h % 2, : w - w % 2],)
    gray = _gray(rgb)
    tiles = []
    for y in range(0, h - size + 1, size):
        for x in range(0, w - size + 1, size):
            tiles.append((float(gray[y:y + size, x:x + size].var()), y, x))
    tiles.sort(reverse=True)
    return tuple(rgb[y:y + size, x:x + size] for _, y, x in tiles[:k])


def laplacian_variance(gray: np.ndarray) -> float:
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return float(lap.var())


def blockiness(gray: np.ndarray, block: int = 8) -> float:
    """8화소 경계의 수평 차분 / 경계 밖 차분. 1 근처면 블록 흔적 없음."""
    d = np.abs(np.diff(gray, axis=1))
    if d.shape[1] < block * 2:
        return 1.0
    cols = np.arange(d.shape[1])
    edge = (cols % block) == block - 1
    return float(d[:, edge].mean() / (d[:, ~edge].mean() + 1e-6))


def estimate_quality(frames: list[Frame]) -> QualityMetrics:
    ref = frames[len(frames) // 2].pixels
    gray = _gray(ref)
    h, w = gray.shape
    sharp = float(np.median([laplacian_variance(_gray(f.pixels)) for f in frames[:: max(1, len(frames) // 4)]]))
    blk = blockiness(gray)
    low = min(h, w) < MIN_SIDE or sharp < MIN_SHARPNESS or blk > MAX_BLOCKINESS
    return QualityMetrics(width=w, height=h, sharpness=sharp, blockiness=blk, low_quality=low)


# ---------- 이미지 트랙 ----------

def bundle_from_image(data: bytes, filename: str | None = None) -> FrameBundle:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img).convert("RGB")
    pixels = np.asarray(img)
    frame = Frame(pixels=pixels, patches=select_patches(pixels))
    return FrameBundle(Track.IMAGE, [frame], estimate_quality([frame]),
                       raw_bytes=data, metadata={"filename": filename})


# ---------- 영상 트랙 ----------

def probe_video(path: Path) -> dict[str, Any]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate:format=duration",
         "-of", "json", str(path)],
        capture_output=True, check=True, text=True)
    info = json.loads(out.stdout)
    stream = info["streams"][0]
    num, den = (int(x) for x in stream["r_frame_rate"].split("/"))
    return {"width": int(stream["width"]), "height": int(stream["height"]),
            "fps": num / den if den else 0.0,
            "duration": float(info["format"].get("duration", 0.0))}


def read_clip(path: Path, start: float, n_frames: int, width: int, height: int) -> list[np.ndarray]:
    """start초부터 연속 n_frames를 원본 해상도 RGB로 디코딩."""
    proc = subprocess.run(
        # -noautorotate: ffprobe가 보고한 (회전 전) 크기와 디코딩 크기를 일치시킨다
        ["ffmpeg", "-v", "error", "-noautorotate", "-ss", f"{start:.3f}", "-i", str(path),
         "-frames:v", str(n_frames), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
        capture_output=True, check=True)
    frame_bytes = width * height * 3
    count = len(proc.stdout) // frame_bytes
    buf = np.frombuffer(proc.stdout[: count * frame_bytes], dtype=np.uint8)
    return list(buf.reshape(count, height, width, 3))


def bundle_from_video(path: Path, metadata: dict[str, Any] | None = None,
                      clip_len: int = CLIP_LEN) -> FrameBundle:
    info = probe_video(path)
    fps = info["fps"] or 30.0
    duration = info["duration"]
    frames: list[Frame] = []
    for segment, point in BIOPSY_POINTS.items():
        start = max(0.0, min(duration * point, duration - clip_len / fps))
        for i, px in enumerate(read_clip(path, start, clip_len, info["width"], info["height"])):
            frames.append(Frame(
                pixels=px, index=round(start * fps) + i, timestamp=start + i / fps,
                segment=segment,
                patches=select_patches(px) if i % PATCH_EVERY == 0 else ()))
    if not frames:
        raise ValueError("영상에서 프레임을 디코딩하지 못했습니다")
    return FrameBundle(Track.VIDEO, frames, estimate_quality(frames), source_path=path,
                       metadata={**(metadata or {}), **info})


def download_youtube(url: str, out_dir: Path) -> tuple[Path, dict[str, Any]]:
    """yt-dlp로 영상 스트림만 받는다. (경로, {video_id, channel_id, channel, title})"""
    import yt_dlp

    out_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        "format": "bv*[height<=1080][ext=mp4]/bv*[height<=1080]/b",
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "noprogress": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
    return path, {
        "video_id": info.get("id"),
        "channel_id": info.get("channel_id"),
        "channel": info.get("channel") or info.get("uploader"),
        "title": info.get("title"),
        "url": url,
    }
