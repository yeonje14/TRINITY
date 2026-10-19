"""비전 인코더 슬롯 — CLIP/DINOv2 등 동결 인코더를 교체 가능하게 둔다.

인코더는 (N, D) L2 정규화 특징을 반환하기만 하면 된다.
transformers/torch가 없으면 load_encoder()는 None을 돌려주고 제3축 분포 편차는 비활성된다.
"""
from __future__ import annotations

from typing import Protocol

import numpy as np

DEFAULT_MODEL = "openai/clip-vit-base-patch32"


class VisionEncoder(Protocol):
    name: str
    dim: int

    def encode(self, images: list[np.ndarray]) -> np.ndarray:
        """RGB uint8 (H,W,3) 목록 → (N, D) float32, 행마다 L2 정규화."""
        ...


class HFClipEncoder:
    """Hugging Face CLIP 비전 타워. 인코더 입력 리사이즈는 모델 전처리기에 맡긴다
    (제1축과 달리 제3축은 고주파 흔적이 아니라 의미를 보므로 리사이즈가 허용된다)."""

    def __init__(self, model_name: str = DEFAULT_MODEL, device: str = "cpu"):
        import torch
        from transformers import CLIPImageProcessor, CLIPVisionModelWithProjection

        self._torch = torch
        self.processor = CLIPImageProcessor.from_pretrained(model_name)
        self.model = CLIPVisionModelWithProjection.from_pretrained(model_name).eval().to(device)
        self.device = device
        self.name = model_name
        self.dim = self.model.config.projection_dim

    def encode(self, images: list[np.ndarray]) -> np.ndarray:
        inputs = self.processor(images=list(images), return_tensors="pt").to(self.device)
        with self._torch.no_grad():
            emb = self.model(**inputs).image_embeds
        emb = emb / emb.norm(dim=-1, keepdim=True)
        return emb.cpu().numpy().astype(np.float32)


def load_encoder(model_name: str = DEFAULT_MODEL, device: str = "cpu") -> VisionEncoder | None:
    try:
        return HFClipEncoder(model_name, device)
    except Exception:  # 미설치·오프라인 등 — 축을 끄고 사유를 남긴다
        return None
