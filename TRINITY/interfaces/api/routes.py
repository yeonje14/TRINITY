"""Flutter용 REST 엔드포인트.

- POST /analyze/url    유튜브 링크 → job_id (비동기, 폴링으로 진행률·결과 조회)
- POST /analyze/image  이미지 업로드 → 결과 (동기 — 처리 시간이 짧음)
- GET  /jobs/{job_id}
- GET  /analyses/{analysis_id}
- GET  /history
- GET  /channels/{channel_id}
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from .pipeline import TrinityPipeline
from .schemas import (AnalysisResult, AnalyzeUrlRequest, ChannelSummary, HistoryItem,
                      JobCreated, JobOut, JobState)
from .store import Store

log = logging.getLogger("trinity.api")
router = APIRouter()

MAX_IMAGE_BYTES = 20 * 1024 * 1024


def _pipeline(request: Request) -> TrinityPipeline:
    return request.app.state.pipeline


def _store(request: Request) -> Store:
    return request.app.state.store


def _run_url_job(pipeline: TrinityPipeline, store: Store, job_id: str, url: str) -> None:
    store.update_job(job_id, state=JobState.RUNNING, progress=0.0, stage="starting")
    try:
        result = pipeline.analyze_url(
            url, progress=lambda p, s: store.update_job(job_id, progress=p, stage=s))
        store.save_analysis(result)
        store.update_job(job_id, state=JobState.DONE, progress=1.0, stage="done",
                         result_id=result.id)
    except Exception as exc:
        log.exception("작업 실패: %s", job_id)
        store.update_job(job_id, state=JobState.FAILED, stage="failed", error=str(exc))


@router.post("/analyze/url", response_model=JobCreated, status_code=202)
def analyze_url(body: AnalyzeUrlRequest, request: Request) -> JobCreated:
    store = _store(request)
    job_id = store.create_job()
    # 단일 워커 큐 — 팬리스 맥북의 열 스로틀링을 감안해 영상 분석은 한 번에 하나씩
    request.app.state.jobs.submit(_run_url_job, _pipeline(request), store, job_id, body.url)
    return JobCreated(job_id=job_id)


@router.post("/analyze/image", response_model=AnalysisResult)
async def analyze_image(request: Request, file: UploadFile = File(...)) -> AnalysisResult:
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "이미지는 20MB 이하만 지원합니다")
    try:
        result = await run_in_threadpool(_pipeline(request).analyze_image, data, file.filename)
    except (OSError, ValueError) as exc:  # PIL 디코딩 실패
        raise HTTPException(400, f"이미지를 읽을 수 없습니다: {exc}") from exc
    _store(request).save_analysis(result)
    return result


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, request: Request) -> JobOut:
    job = _store(request).get_job(job_id)
    if job is None:
        raise HTTPException(404, "작업을 찾을 수 없습니다")
    return job


@router.get("/analyses/{analysis_id}", response_model=AnalysisResult)
def get_analysis(analysis_id: str, request: Request) -> AnalysisResult:
    result = _store(request).get_analysis(analysis_id)
    if result is None:
        raise HTTPException(404, "분석 결과를 찾을 수 없습니다")
    return result


@router.get("/history", response_model=list[HistoryItem])
def history(request: Request, limit: int = Query(50, ge=1, le=200)) -> list[HistoryItem]:
    return _store(request).history(limit)


@router.get("/channels/{channel_id}", response_model=ChannelSummary)
def channel(channel_id: str, request: Request) -> ChannelSummary:
    summary = _store(request).channel_summary(channel_id)
    if summary is None:
        raise HTTPException(404, "이 채널의 분석 이력이 없습니다")
    return summary
