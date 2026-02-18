# 🛡️ TRINITY: The 3-Axis Multi-modal AI Video Detective

> **"화질이 낮으면 움직임(물리)을, 화질이 높으면 픽셀(디지털) 흔적을 본다."**  
> **"Low quality? Check motion & consistency. High quality? Check visual artifacts."**  
> **「低画質なら動きと一貫性、高画質なら視覚的アーティファクトを確認する。」**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyTorch MPS](https://img.shields.io/badge/PyTorch-MPS%20Accelerated-E9967A.svg)](https://pytorch.org/)
[![Hardware: Apple Silicon](https://img.shields.io/badge/Hardware-Apple%20Silicon-000000.svg)](https://www.apple.com/macbook-air/)
[![Service: KakaoTalk Chatbot](https://img.shields.io/badge/Service-KakaoTalk%20Chatbot-F7E600.svg)](https://i.kakao.com/)

---

### 🌍 Language Select
[🇰🇷 **한국어 (Korean)**](#-한국어-korean) | [🇺🇸 **English**](#-english) | [🇯🇵 **日本語 (Japanese)**](#-日本語-japanese)

---

## 📂 Project Structure

```
TRINITY/
├── 📂 interfaces/           # [KR] 사용자 인터페이스 어댑터 / [EN] User Interface Adapters / [JP] ユーザーインターフェース
│   └── 📂 kakao/            # [KR] 카카오톡 챗봇 서비스 / [EN] KakaoTalk Chatbot Service / [JP] カカオトークチャットボット
│       ├── routes.py        # [KR] 웹훅 핸들러 / [EN] Webhook Handler / [JP] Webhookハンドラー
│       └── templates.py     # [KR] 응답 템플릿 (기본 카드) / [EN] Response Templates (BasicCard) / [JP] 応答テンプレート (基本カード)
│
├── 📂 core/                 # [KR] 3축 탐지 엔진 (핵심) / [EN] The 3-Axis Detection Engine / [JP] 3軸検知エンジン (コア)
│   ├── 📂 axis_a/           # [KR] [물리] 시간적 일관성 / [EN] [Physical] Temporal Consistency / [JP] [物理] 時間的一貫性
│   │   ├── geometry.py      # [KR] 3D 헤드 포즈 불일치 분석 / [EN] Head Pose Inconsistency / [JP] 3Dヘッドポーズ不一致分析
│   │   └── lip_sync.py      # [KR] 의미론적 떨림 및 위상 지연 / [EN] Semantic Jitter & Phase Lag / [JP] 意味論的ジッターと位相遅延
│   ├── 📂 axis_b/           # [KR] [생체] 생체 신호 감지 / [EN] [Bio] Physiological Signal / [JP] [生体] 生体信号検知
│   │   ├── evm.py           # [KR] 영상 색상 증폭 기술 / [EN] Eulerian Video Magnification / [JP] 映像色増幅技術 (EVM)
│   │   └── rppg.py          # [KR] 심박 신호 추출 (FFT) / [EN] Heartbeat Signal Extraction / [JP] 心拍信号抽出 (FFT)
│   ├── 📂 axis_c/           # [KR] [시각] 디지털 아티팩트 / [EN] [Visual] Digital Artifacts / [JP] [視覚] デジタルアーティファクト
│   │   ├── efficientnet.py  # [KR] EfficientNet (MPS 가속) / [EN] EfficientNet-B0 (MPS Optimized) / [JP] EfficientNet (MPS加速)
│   │   └── artifacts.py     # [KR] 격자무늬 패턴 탐지 / [EN] Checkerboard Pattern Detection / [JP] 格子模様パターン検知
│   └── ensemble.py          # [KR] 가중치 투표 알고리즘 / [EN] Weighted Voting Algorithm / [JP] 加重投票アルゴリズム
│
├── 📂 preprocessing/        # [KR] 스마트 영상 전처리 / [EN] Smart Video Processing / [JP] スマート映像前処理
│   ├── biopsy.py            # [KR] 3-Point 생체검사 (10초 샘플링) / [EN] "3-Point Biopsy" (Sampling 10s clips) / [JP] 3点生検 (10秒サンプリング)
│   ├── ffmpeg.py            # [KR] 하드웨어 가속 디코딩 / [EN] Hardware Accelerated Decoding / [JP] ハードウェアアクセラレーションデコード
│   └── frames.py            # [KR] 정규화 및 리사이징 / [EN] Normalization & Resizing / [JP] 正規化およびリサイズ
│
├── 📂 infrastructure/       # [KR] 서버 설정 / [EN] Server Configuration / [JP] サーバー設定
│   ├── celery_app.py        # [KR] 비동기 작업 관리자 (Redis) / [EN] Async Task Manager (Redis) / [JP] 非同期タスク管理 (Redis)
│   ├── config.py            # [KR] M4 Metal(MPS) 설정 / [EN] M4 Metal(MPS) Settings / [JP] M4 Metal(MPS)設定
│   └── logging.py           # [KR] 시스템 모니터링 / [EN] System Monitoring / [JP] システムモニタリング
│
├── 📂 jobs/                 # [KR] 백그라운드 작업 / [EN] Background Tasks / [JP] バックグラウンドタスク
│   ├── tasks.py             # [KR] 분석 워크플로우 정의 / [EN] Analysis Workflow Definition / [JP] 分析ワークフロー定義
│   └── schemas.py           # [KR] 데이터 유효성 검사 (Pydantic) / [EN] Data Validation (Pydantic) / [JP] データバリデーション (Pydantic)
│
├── 📂 storage/              # [KR] I/O 관리 / [EN] I/O Management / [JP] I/O管理
│   ├── cache.py             # [KR] Redis 인터페이스 / [EN] Redis Interface / [JP] Redisインターフェース
│   └── model_registry.py    # [KR] 모델 로딩 및 버전 관리 / [EN] Model Loading & Versioning / [JP] モデル読み込みとバージョン管理
│
├── 📂 deploy/               # [KR] 배포 설정 / [EN] Deployment Configs / [JP] デプロイ設定
│   └── 📂 cloudflare/
│       └── tunnel.yml       # [KR] 보안 터널 설정 / [EN] Secure Tunneling Setup / [JP] セキュアトンネル設定
│
├── 📂 weights/              # [KR] 학습된 모델 가중치 (.pth) / [EN] Pre-trained Model Weights / [JP] 学習済みモデルの重み
├── app.py                   # [KR] 메인 애플리케이션 진입점 / [EN] Main Application Entry Point / [JP] メインアプリケーションエントリーポイント
└── requirements.txt         # [KR] Python 의존성 목록 / [EN] Python Dependencies / [JP] Python依存関係リスト
```
---


> ⚠️ **Research Prototype / Under Active Development**  
> This repository is a research/engineering prototype. Results, thresholds, and performance metrics will be updated as experiments progress.

---

<br>

## 🇰🇷 한국어 (Korean)

### 1. 프로젝트 개요 (Overview)
**TRINITY**는 단일 모델 기반 탐지기의 한계를 보완하기 위해, 서로 다른 성격의 단서를 결합하는 **3축(Temporal / Physiological / Visual) 앙상블 AI 영상 탐지 시스템**입니다.

- **환경:** **MacBook Air (M4)** 등 Apple Silicon (PyTorch **MPS** 가속 활용)
- **목표:** 다양한 화질/압축/생성 방식 조건에서의 **강건성(Robustness)**을 높이고, **카카오톡 챗봇** 기반의 간편한 인터페이스로 디지털 취약 계층(노년층)의 접근성을 강화합니다.

---

### 2. 시스템 파이프라인 (Pipeline)
**"요청 → 비동기 분석 → 결과 반환" (저비용·재현 가능한 구조)**

1. **Interface:** 카카오톡 챗봇으로 의심 영상(또는 유튜브 링크) 전송  
2. **Network:** **Cloudflare Tunnel** 기반 HTTPS 터널링 (유동 IP/포트포워딩 이슈 최소화)  
3. **Control:** **Flask + Celery + Redis**로 요청을 큐에 적재하고 워커가 비동기 처리  
4. **Preprocessing:** `yt-dlp` 기반 **3-Point Biopsy** (전/중/후 10초 구간 추출) + `ffmpeg` 정규화  
5. **Acceleration:** C축 모델 추론은 **PyTorch MPS(Metal)**로 Apple Silicon GPU 가속 활용

> ✅ **설계 포인트:** 축별 분석은 독립 모듈로 분리하여 병렬/비동기 처리에 적합하게 구성합니다.

---

### 3. 핵심 분석 엔진: Trinity 3-Axis
본 시스템은 “단일 CNN만으로는 놓칠 수 있는 경우”를 줄이기 위해, 서로 다른 단서(시간/생체/시각)를 결합합니다.

#### **A축: 시간적 일관성 (Temporal Consistency)**
> *"합성 과정에서 프레임 간 기하학적·시계열적 불일치가 발생할 수 있다."*

- **A1. Head Pose Inconsistency**
  - **원리:** 얼굴 합성으로 인해 **내부(중심부) 랜드마크 기반 포즈**와 **외곽(윤곽) 랜드마크 기반 포즈** 추정 간 불일치가 나타날 수 있음.
  - **구현:** MediaPipe Face Mesh(468) 기반 포즈 추정 + 프레임 간 오차/변화율 통계.
  - **Reference:** [ICASSP 2019 — Exposing DeepFakes Using Inconsistent Head Poses](https://arxiv.org/pdf/1811.00661.pdf)

- **A2. Lip Temporal Irregularity**
  - **원리:** 입술/턱 주변의 시계열 표현에서 비정상적 불규칙성(temporal irregularity)이 나타날 수 있음.
  - **구현:** 입술 랜드마크 기반 지표(MAR 등) 시계열 + 주파수/변동성 통계.
  - **Reference:** [CVPR 2021 — LipForensics](https://arxiv.org/pdf/2011.06734.pdf)

#### **B축: 생체 신호 (Physiological / rPPG)**
> *"실제 인물 영상은 혈류 기반의 주기 신호(rPPG)를 포함할 수 있다."*

- **원리:** ROI(양 볼/이마)의 채널 시계열을 추출해 **FFT**로 심박 대역(예: 0.7–4Hz)의 신호 특징(피크/SNR)을 분석.
- **옵션:** 저화질/압축 환경에서는 **EVM**을 선택적으로 적용하여 미세 변화 신호를 보강(게이팅 기반).
- **Reference:** [IEEE TPAMI — FakeCatcher](https://arxiv.org/pdf/1901.02212.pdf)

#### **C축: 시각적 아티팩트 (Visual & Pattern)**
> *"생성 과정은 시각적으로 미세한 아티팩트/통계적 패턴을 남길 수 있다."*

- **C1. Pattern Detective (Benchmark-driven)**
  - **원리:** 표준 벤치마크(FF++) 기반으로 학습된 모델이 합성 흔적을 식별하도록 구성.
  - **구현:** FaceForensics++(c40 등 압축 조건 포함) 기반 전이학습/평가.
  - **Reference:** [ICCV 2019 — FaceForensics++](https://arxiv.org/pdf/1901.08971.pdf)

- **C2. Microscope Analyst (Efficient Backbone)**
  - **원리:** 경량 모델(EfficientNet-B0)로 저자원 환경에서 효율적으로 추론.
  - **구현:** EfficientNet-B0 + Apple Silicon **MPS** 가속.
  - **Reference:** [ICML 2019 — EfficientNet](https://arxiv.org/pdf/1905.11946.pdf)

---

### 4. 하드웨어 최적화 (Apple Silicon)
- **MPS (Metal Performance Shaders):** PyTorch `mps` 백엔드로 Apple Silicon GPU 가속 활용  
- **Unified Memory:** CPU-GPU 메모리 공유 구조 활용 (고해상도 처리 병목 완화)  
- **Green Computing:** 저전력 환경에서 지속 가능한 홈 서버 운영 목표  

---

### 5. 제한 및 주의 (Limitations)
- 저조도/강한 모션/과도한 압축 환경에서는 B축(rPPG)의 신뢰도가 저하될 수 있어 품질 게이팅을 적용합니다.
- A축은 공개된 대중 SaaS 사례는 제한적이나, 국제 학회 논문 기반으로 경량 구현 및 실험 검증을 목표로 합니다.
- 본 프로젝트는 **위험도(risk score)** 기반으로 결과를 제시하며, 단정적 판정의 오용을 방지합니다.

---

<br>

## 🇺🇸 English

### 1. Project Overview
**TRINITY** is a **3-axis ensemble AI Video detection system** that combines **Temporal**, **Physiological**, and **Visual** cues to improve robustness beyond single-modal detectors.

- **Environment:** Apple Silicon (e.g., MacBook Air M4) with **PyTorch MPS** acceleration
- **Goal:** Improve robustness across compression/quality/generation conditions and provide an accessible interface via a **KakaoTalk chatbot**.

---

### 2. System Pipeline
**Request → Async Analysis → Response (low-cost & reproducible)**

1. **Interface:** User sends a suspicious video (or YouTube URL)  
2. **Network:** HTTPS tunneling via **Cloudflare Tunnel**  
3. **Control:** **Flask + Celery + Redis** queue-based async processing  
4. **Preprocessing:** `yt-dlp` **3-Point Biopsy** (start/mid/end 10s clips) + `ffmpeg` normalization  
5. **Acceleration:** Visual inference on Apple Silicon GPU via **PyTorch MPS (Metal)**

---

### 3. Core Engine: Trinity 3-Axis

#### **Axis A: Temporal Consistency**
> *AI Video synthesis may introduce geometric and temporal inconsistencies.*

- **A1. Head Pose Inconsistency**
  - **Idea:** Pose estimated from inner facial landmarks can disagree with pose from outer contours.
  - **Impl:** MediaPipe Face Mesh + statistical inconsistency metrics.
  - **Ref:** [ICASSP 2019 — Inconsistent Head Poses](https://arxiv.org/pdf/1811.00661.pdf)

- **A2. Lip Temporal Irregularity**
  - **Idea:** Subtle temporal irregularities may appear in lip/jaw dynamics.
  - **Impl:** Landmark-based mouth ratio time-series + frequency/variance statistics.
  - **Ref:** [CVPR 2021 — LipForensics](https://arxiv.org/pdf/2011.06734.pdf)

#### **Axis B: Physiological / rPPG**
> *Real videos may contain periodic blood-flow signals; synthetic ones may weaken them.*

- **Idea:** Extract ROI color signals and apply **FFT** to inspect heart-rate band features (peak/SNR).
- **Option:** Apply **EVM** selectively under heavy compression (gating-based).
- **Ref:** [IEEE TPAMI — FakeCatcher](https://arxiv.org/pdf/1901.02212.pdf)

#### **Axis C: Visual & Pattern**
> *Generation pipelines can leave subtle artifacts/statistical fingerprints.*

- **C1. Pattern Detective (Benchmark-driven)**
  - **Idea:** Learn artifact patterns using a standard benchmark (FF++).
  - **Impl:** Transfer learning / evaluation on FaceForensics++ (including compressed settings).
  - **Ref:** [ICCV 2019 — FaceForensics++](https://arxiv.org/pdf/1901.08971.pdf)

- **C2. Microscope Analyst (Efficient Backbone)**
  - **Idea:** EfficientNet-B0 for edge-friendly inference.
  - **Impl:** EfficientNet-B0 accelerated with **PyTorch MPS**.
  - **Ref:** [ICML 2019 — EfficientNet](https://arxiv.org/pdf/1905.11946.pdf)

---

### 4. Apple Silicon Optimization
- **MPS Acceleration:** `torch.device("mps")` for Apple Silicon GPU acceleration  
- **Unified Memory:** reduces data transfer overhead  
- **Green Computing:** energy-efficient home-server operation goal  

---

### 5. Limitations
- rPPG may degrade under low light / strong motion / heavy compression; quality gating is applied.
- Axis A is less common in publicly exposed SaaS, but is supported by peer-reviewed literature and will be validated experimentally.
- Results are presented as a **risk score**, not a definitive verdict.

---

<br>

## 🇯🇵 日本語 (Japanese)

### 1. プロジェクト概要
**TRINITY**は、単一モダリティ検知の限界を補うために、**時間的一貫性（Temporal）・生体信号（Physiological）・視覚的アーティファクト（Visual）**を統合する**3軸アンサンブル検知システム**です。

- **環境:** Apple Silicon（例：MacBook Air M4）+ PyTorch **MPS** 加速  
- **目的:** 圧縮・画質・生成手法の違いに対する**堅牢性**を高め、**KakaoTalkチャットボット**で高いアクセス性を提供します。

---

### 2. システムパイプライン
**リクエスト → 非同期解析 → 結果返却（低コスト・再現可能）**

1. **Interface:** KakaoTalkで疑わしい動画（またはYouTube URL）を送信  
2. **Network:** **Cloudflare Tunnel** によるHTTPSトンネリング  
3. **Control:** **Flask + Celery + Redis** によるキュー型の非同期処理  
4. **Preprocessing:** `yt-dlp` の **3点生検（開始/中間/終盤10秒）** + `ffmpeg` 正規化  
5. **Acceleration:** 視覚モデル推論は **PyTorch MPS（Metal）** でApple Silicon GPU加速

---

### 3. コア分析：Trinity 3-Axis

#### **A軸：時間的一貫性（Temporal Consistency）**
> *合成は幾何学的・時系列的な不整合を生む可能性がある。*

- **A1. Head Pose Inconsistency**
  - **考え方:** 内部ランドマークと外郭ランドマークで推定した姿勢が不一致になる場合がある。
  - **実装:** MediaPipe Face Mesh + 不一致の統計指標。
  - **Ref:** [ICASSP 2019](https://arxiv.org/pdf/1811.00661.pdf)

- **A2. Lip Temporal Irregularity**
  - **考え方:** 口唇/顎の動きに微細な時系列不規則性が出る場合がある。
  - **実装:** 口唇比率(MAR等)の時系列 + 周波数/分散統計。
  - **Ref:** [CVPR 2021](https://arxiv.org/pdf/2011.06734.pdf)

#### **B軸：生体信号（Physiological / rPPG）**
> *実映像には血流由来の周期信号が含まれる場合がある。*

- **考え方:** ROIの色信号を抽出し、**FFT**で心拍帯域の特徴（ピーク/SNR）を分析。
- **オプション:** 圧縮が強い場合は **EVM** を選択的に適用（ゲーティング）。
- **Ref:** [IEEE TPAMI](https://arxiv.org/pdf/1901.02212.pdf)

#### **C軸：視覚的アーティファクト（Visual & Pattern）**
> *生成パイプラインは微細なアーティファクト/統計的指紋を残す可能性がある。*

- **C1. Pattern Detective（ベンチマーク基盤）**
  - **考え方:** 標準ベンチマーク（FF++）によりアーティファクトを学習。
  - **実装:** FaceForensics++（圧縮条件含む）で転移学習/評価。
  - **Ref:** [ICCV 2019](https://arxiv.org/pdf/1901.08971.pdf)

- **C2. Microscope Analyst（軽量バックボーン）**
  - **考え方:** EfficientNet-B0 によりエッジ環境でも効率的に推論。
  - **実装:** EfficientNet-B0 + PyTorch **MPS** 加速。
  - **Ref:** [ICML 2019](https://arxiv.org/pdf/1905.11946.pdf)

---

### 4. Apple Silicon 最適化
- **MPS加速:** `torch.device("mps")` によるGPU加速  
- **ユニファイドメモリ:** データ転送のオーバーヘッドを低減  
- **省電力運用:** 低消費電力のホームサーバー運用を目標  

---

### 5. 制限事項（Limitations）
- 低照度/強いモーション/強圧縮ではB軸（rPPG）の信頼性が低下するため品質ゲーティングを適用します。
- A軸は公開SaaSで一般的ではないものの、査読付き論文に基づき実験で妥当性を検証します。
- 本システムは「確定判定」ではなく **リスクスコア**として結果を提示します。

---

## 📚 References
1. **[A-Axis]** Yang et al., *"Exposing DeepFakes Using Inconsistent Head Poses"*, ICASSP 2019 — https://arxiv.org/pdf/1811.00661.pdf  
2. **[A-Axis]** Haliassos et al., *"LipForensics: Irregularities in Semantic High-Level Representations"*, CVPR 2021 — https://arxiv.org/pdf/2011.06734.pdf  
3. **[B-Axis]** Demir et al., *"FakeCatcher: Detection of Synthetic Portrait Videos using Biological Signals"*, IEEE TPAMI — https://arxiv.org/pdf/1901.02212.pdf  
4. **[C-Axis]** Rössler et al., *"FaceForensics++: Learning to Detect Manipulated Facial Images"*, ICCV 2019 — https://arxiv.org/pdf/1901.08971.pdf  
5. **[C-Axis]** Tan et al., *"EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks"*, ICML 2019 — https://arxiv.org/pdf/1905.11946.pdf  

---
© 2026 TRINITY Project. Developed by Yeonje Lee.
