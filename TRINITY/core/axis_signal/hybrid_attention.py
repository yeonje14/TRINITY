"""축1-B: 공간-주파수 하이브리드 어텐션 (학습형).

공간 분기(RGB) + 주파수 분기(로그 진폭 스펙트럼)를 각각 CBAM으로 정제한 뒤
게이트로 융합한다. 현재는 구조만 있고 가중치는 미학습 상태 (README §10).
torch가 없거나 가중치 파일이 없으면 UNAVAILABLE을 반환한다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from core.contracts import AxisName, AxisResult, AxisStatus, Evidence, FrameBundle

try:
    import torch
    from torch import nn
    import torch.nn.functional as F
except ImportError:  # torch는 선택 의존성
    torch = None

PATCH = 256

if torch is not None:

    class ChannelAttention(nn.Module):
        def __init__(self, c: int, reduction: int = 8):
            super().__init__()
            self.mlp = nn.Sequential(
                nn.Conv2d(c, c // reduction, 1, bias=False), nn.ReLU(inplace=True),
                nn.Conv2d(c // reduction, c, 1, bias=False))

        def forward(self, x):
            avg = self.mlp(F.adaptive_avg_pool2d(x, 1))
            mx = self.mlp(F.adaptive_max_pool2d(x, 1))
            return x * torch.sigmoid(avg + mx)

    class SpatialAttention(nn.Module):
        def __init__(self, k: int = 7):
            super().__init__()
            self.conv = nn.Conv2d(2, 1, k, padding=k // 2, bias=False)

        def forward(self, x):
            s = torch.cat([x.mean(1, keepdim=True), x.amax(1, keepdim=True)], 1)
            return x * torch.sigmoid(self.conv(s))

    class CBAM(nn.Module):
        def __init__(self, c: int):
            super().__init__()
            self.ca, self.sa = ChannelAttention(c), SpatialAttention()

        def forward(self, x):
            return self.sa(self.ca(x))

    def _branch(in_ch: int, widths=(32, 64, 128)) -> nn.Sequential:
        layers, c = [], in_ch
        for w in widths:
            layers += [nn.Conv2d(c, w, 3, stride=2, padding=1, bias=False),
                       nn.BatchNorm2d(w), nn.ReLU(inplace=True), CBAM(w)]
            c = w
        layers.append(nn.AdaptiveAvgPool2d(1))
        return nn.Sequential(*layers)

    class HybridAttentionNet(nn.Module):
        """입력: rgb (B,3,H,W) [0,1], spec (B,1,H,W) 정규화된 로그 진폭. 출력: logit (B,)."""

        def __init__(self, dim: int = 128):
            super().__init__()
            self.spatial = _branch(3)
            self.freq = _branch(1)
            self.gate = nn.Linear(2 * dim, dim)
            self.head = nn.Sequential(nn.Dropout(0.2), nn.Linear(dim, 1))

        def forward(self, rgb, spec):
            fs = self.spatial(rgb).flatten(1)
            ff = self.freq(spec).flatten(1)
            g = torch.sigmoid(self.gate(torch.cat([fs, ff], 1)))
            return self.head(g * fs + (1 - g) * ff).squeeze(1)


def to_inputs(patch: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(H,W,3) uint8 패치 → (rgb (3,H,W), spec (1,H,W)) float32."""
    rgb = patch.astype(np.float32).transpose(2, 0, 1) / 255.0
    gray = rgb.mean(0)
    amp = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(gray - gray.mean()))))
    amp = (amp - amp.mean()) / (amp.std() + 1e-6)
    return rgb, amp[None].astype(np.float32)


class HybridSignalModel:
    name = AxisName.SIGNAL

    def __init__(self, weights: Path | None = None, device: str = "cpu"):
        self.model = None
        self.reason = None
        if torch is None:
            self.reason = "torch 미설치"
        elif weights is None or not Path(weights).exists():
            self.reason = "학습된 가중치 없음"
        else:
            self.model = HybridAttentionNet()
            self.model.load_state_dict(torch.load(weights, map_location=device))
            self.model.eval().to(device)
            self.device = device

    @property
    def available(self) -> bool:
        return self.model is not None

    def analyze(self, bundle: FrameBundle) -> AxisResult:
        if not self.available:
            return AxisResult(self.name, AxisStatus.UNAVAILABLE, gate_reason=f"축1-B: {self.reason}")
        patches = [p for f in bundle.frames for p in f.patches
                   if p.shape[0] == PATCH and p.shape[1] == PATCH]
        if not patches:
            return AxisResult(self.name, AxisStatus.NOT_APPLICABLE,
                              gate_reason=f"축1-B: {PATCH}px 패치 없음")
        rgb, spec = zip(*(to_inputs(p) for p in patches))
        with torch.no_grad():
            logits = self.model(torch.from_numpy(np.stack(rgb)).to(self.device),
                                torch.from_numpy(np.stack(spec)).to(self.device))
        probs = torch.sigmoid(logits).cpu().numpy()
        return AxisResult(
            self.name, AxisStatus.OK, score=float(np.median(probs)),
            confidence=float(1.0 - min(np.std(probs) * 2, 1.0)),
            evidence=[Evidence("signal.hybrid", "공간-주파수 하이브리드 모델 판정", None)],
            details={"scorer": "hybrid_attention", "patch_scores": probs.round(4).tolist()},
        )
