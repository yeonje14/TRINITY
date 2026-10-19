# TRINITY v4 — 서버 코드

설계·근거·문헌은 [루트 README](../README.md)를 참고하세요. 이 문서는 실행 방법만 다룹니다.

## 실행

```bash
brew install ffmpeg                 # 영상 디코딩 (ffmpeg / ffprobe)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

- API 문서: http://localhost:8000/docs
- 외부 데모 노출: `deploy/cloudflare/tunnel.yml` 참고

## 테스트

```bash
pytest
```

합성 데이터로 **판정 순서와 근거 방향**만 검증합니다. 절대 성능은 실제 벤치마크로 재보정한 뒤에만 주장합니다.

## 선택 구성요소 (환경변수)

| 변수 | 역할 | 없을 때 |
|---|---|---|
| `TRINITY_SIGNAL_WEIGHTS` | 축1-B 하이브리드 어텐션 가중치 `.pt` (torch 필요) | 축1-A 규칙 기반만 동작 |
| `TRINITY_SEMANTIC_ENCODER` | 비전 인코더 이름 (예: `openai/clip-vit-base-patch32`, transformers 필요) | 분포 편차 비활성 |
| `TRINITY_REFERENCE` | 참조 분포 `.npz` (`ReferenceDistribution.fit(...).save(...)`) | 분포 편차 비활성 |
| `TRINITY_DB` | SQLite 경로 (기본 `trinity.db`) | — |

`c2pa-python`이 설치되어 있으면 C2PA 서명까지 검증하고, 없으면 컨테이너 스캔으로 매니페스트 존재·주장만 읽습니다.
SynthID 워터마크 탐지기는 `core/axis_provenance/synthid.py`의 `WatermarkDetector` 슬롯에 연결합니다 (현재 미연결 → `UNAVAILABLE`).
