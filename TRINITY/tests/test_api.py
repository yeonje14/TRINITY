import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from datetime import datetime, timezone  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app import create_app  # noqa: E402
from core.ensemble import RiskLevel  # noqa: E402
from interfaces.api.pipeline import TrinityPipeline  # noqa: E402
from interfaces.api.schemas import AnalysisResult, SourceInfo  # noqa: E402
from interfaces.api.store import Store  # noqa: E402
from synthetic import generated, natural, png_bytes  # noqa: E402


@pytest.fixture
def client():
    store = Store(":memory:")
    with TestClient(create_app(TrinityPipeline(), store)) as c:
        c.store = store
        yield c


def test_image_end_to_end(client):
    r = client.post("/analyze/image", files={"file": ("a.png", png_bytes(generated()), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["track"] == "image"
    assert {a["axis"] for a in body["axes"]} == {"signal", "provenance", "semantic"}
    prov = next(a for a in body["axes"] if a["axis"] == "provenance")
    assert prov["status"] == "no_evidence" and prov["weight"] == 0
    assert client.get("/history").json()[0]["id"] == body["id"]
    assert client.get(f"/analyses/{body['id']}").json()["score"] == body["score"]
    assert client.get("/analyses/nope").status_code == 404


def test_generated_riskier_than_natural(client):
    def score(img):
        return client.post("/analyze/image", files={"file": ("a.png", png_bytes(img))}).json()["score"]
    assert score(generated()) > score(natural())


def test_bad_image_400(client):
    r = client.post("/analyze/image", files={"file": ("a.png", b"not an image")})
    assert r.status_code == 400


def test_url_validation(client):
    assert client.post("/analyze/url", json={"url": "https://example.com/v"}).status_code == 422


def test_unknown_job_404(client):
    assert client.get("/jobs/nope").status_code == 404


def test_channel_summary(client):
    for level in (RiskLevel.HIGH, RiskLevel.LOW, RiskLevel.HIGH):
        client.store.save_analysis(AnalysisResult(
            id=f"id-{level}-{datetime.now().timestamp()}", track="video", risk_level=level,
            score=0.5, confidence=0.5, axes=[],
            source=SourceInfo(channel_id="UC1", channel="Test"),
            created_at=datetime.now(timezone.utc)))
    s = client.get("/channels/UC1").json()
    assert s["analyzed"] == 3 and s["high_risk"] == 2 and len(s["recent"]) == 3
    assert client.get("/channels/UC404").status_code == 404
