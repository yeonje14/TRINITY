"""작업 상태·이력·채널 집계 저장소 (SQLite, 표준 라이브러리만 사용)."""
from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone

from .schemas import AnalysisResult, ChannelSummary, HistoryItem, JobOut, JobState

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY, state TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0,
    stage TEXT, result_id TEXT, error TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY, track TEXT NOT NULL, risk_level TEXT NOT NULL, score REAL,
    channel_id TEXT, channel TEXT, title TEXT, created_at TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_analyses_channel ON analyses(channel_id, created_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str = "trinity.db"):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(_SCHEMA)

    # ---- jobs ----
    def create_job(self) -> str:
        job_id = uuid.uuid4().hex
        with self._lock, self._db:
            self._db.execute("INSERT INTO jobs (id, state, created_at) VALUES (?, ?, ?)",
                             (job_id, JobState.QUEUED.value, _now()))
        return job_id

    def update_job(self, job_id: str, *, state: JobState | None = None,
                   progress: float | None = None, stage: str | None = None,
                   result_id: str | None = None, error: str | None = None) -> None:
        fields = {"state": state.value if state else None, "progress": progress,
                  "stage": stage, "result_id": result_id, "error": error}
        sets = {k: v for k, v in fields.items() if v is not None}
        if not sets:
            return
        with self._lock, self._db:
            self._db.execute(
                f"UPDATE jobs SET {', '.join(f'{k} = ?' for k in sets)} WHERE id = ?",
                (*sets.values(), job_id))

    def get_job(self, job_id: str) -> JobOut | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        result = self.get_analysis(row["result_id"]) if row["result_id"] else None
        return JobOut(job_id=row["id"], state=JobState(row["state"]), progress=row["progress"],
                      stage=row["stage"], result=result, error=row["error"])

    # ---- analyses ----
    def save_analysis(self, result: AnalysisResult) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO analyses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (result.id, result.track.value, result.risk_level.value, result.score,
                 result.source.channel_id, result.source.channel, result.source.title,
                 result.created_at.isoformat(), result.model_dump_json()))

    def get_analysis(self, analysis_id: str) -> AnalysisResult | None:
        with self._lock:
            row = self._db.execute("SELECT payload FROM analyses WHERE id = ?",
                                   (analysis_id,)).fetchone()
        return AnalysisResult.model_validate_json(row["payload"]) if row else None

    def history(self, limit: int = 50, channel_id: str | None = None) -> list[HistoryItem]:
        sql = "SELECT * FROM analyses"
        args: tuple = ()
        if channel_id:
            sql += " WHERE channel_id = ?"
            args = (channel_id,)
        sql += " ORDER BY created_at DESC LIMIT ?"
        with self._lock:
            rows = self._db.execute(sql, (*args, limit)).fetchall()
        return [HistoryItem(id=r["id"], track=r["track"], risk_level=r["risk_level"],
                            score=r["score"], title=r["title"], channel_id=r["channel_id"],
                            created_at=r["created_at"]) for r in rows]

    def channel_summary(self, channel_id: str, recent: int = 10) -> ChannelSummary | None:
        with self._lock:
            row = self._db.execute(
                """SELECT COUNT(*) AS n,
                          SUM(risk_level = 'high') AS high,
                          SUM(risk_level = 'caution') AS caution,
                          MAX(channel) AS channel
                   FROM analyses WHERE channel_id = ?""", (channel_id,)).fetchone()
        if not row["n"]:
            return None
        return ChannelSummary(channel_id=channel_id, channel=row["channel"], analyzed=row["n"],
                              high_risk=row["high"] or 0, caution=row["caution"] or 0,
                              recent=self.history(recent, channel_id))
