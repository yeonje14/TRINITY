"""FastAPI 진입점.

    uvicorn app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interfaces.api.pipeline import TrinityPipeline
from interfaces.api.routes import router
from interfaces.api.store import Store

logging.basicConfig(level=os.getenv("TRINITY_LOG_LEVEL", "INFO"))


def create_app(pipeline: TrinityPipeline | None = None, store: Store | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pipeline = pipeline or TrinityPipeline()
        app.state.store = store or Store(os.getenv("TRINITY_DB", "trinity.db"))
        app.state.jobs = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trinity-job")
        yield
        app.state.jobs.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(title="TRINITY", version="4.0.0", lifespan=lifespan)
    # Flutter 웹 빌드가 다른 포트에서 호출하므로 CORS 허용 (TRINITY_CORS_ORIGINS=a,b 로 제한 가능)
    app.add_middleware(CORSMiddleware,
                       allow_origins=os.getenv("TRINITY_CORS_ORIGINS", "*").split(","),
                       allow_methods=["*"], allow_headers=["*"])
    app.include_router(router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
