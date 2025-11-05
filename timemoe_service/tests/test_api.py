"""
针对 TimeMoE 推理微服务的精简回归测试。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import pytest
import anyio
import httpx

# 确保可以从 tests 目录导入 app 包
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import fastapi_app  # noqa: E402
from app.api.routes import set_engine  # noqa: E402


class SyncASGIClient:
    """使用 httpx.ASGITransport 的同步封装，兼容新版 httpx。"""

    def __init__(self, app):
        self._transport = httpx.ASGITransport(app=app)
        self._base_kwargs = {"base_url": "http://testserver"}

    async def _request(self, method: str, url: str, **kwargs):
        async with httpx.AsyncClient(transport=self._transport, **self._base_kwargs) as client:
            return await client.request(method, url, **kwargs)

    def request(self, method: str, url: str, **kwargs):
        async def runner():
            return await self._request(method, url, **kwargs)
        return anyio.run(runner)

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def close(self) -> None:
        anyio.run(self._transport.aclose)


class FakeEngine:
    """无需加载真实模型的桩实现，便于接口回归测试。"""

    device = "cpu"

    def is_available(self) -> bool:
        return True

    def predict_aging(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        device_id = payload.get("device_id")
        return {
            "device_id": device_id,
            "health_index": 82.5,
            "tte_hours": 720,
            "rul_hours": 1440,
            "risk_level": "medium",
            "contributors": [
                {"metric": "temperature", "weight": 0.5},
                {"metric": "memory_usage", "weight": 0.3},
                {"metric": "cpu_usage", "weight": 0.2},
            ],
        }

    def predict_fault_trend(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        device_id = payload.get("device_id")
        return {
            "device_id": device_id,
            "prob_7d": 0.2,
            "prob_14d": 0.35,
            "prob_30d": 0.55,
            "risk_level": "high",
            "explanation": "测试桩返回的风险解释",
        }


class UnavailableEngine(FakeEngine):
    def is_available(self) -> bool:
        return False


class ValidationErrorEngine(FakeEngine):
    def predict_aging(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("指标缺失")


class CrashEngine(FakeEngine):
    def predict_fault_trend(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError("推理失败")


@pytest.fixture(scope="module")
def client() -> SyncASGIClient:
    # 移除真实启动事件，避免加载大模型
    fastapi_app.router.on_startup.clear()
    fastapi_app.router.on_shutdown.clear()
    set_engine(FakeEngine())

    client = SyncASGIClient(fastapi_app)
    yield client
    client.close()


def make_payload() -> Dict[str, Any]:
    return {
        "device_id": "dev-001",
        "timestamp": "2025-11-04T15:30:00Z",
        "metrics": {
            "temperature": 65.2,
            "memory_usage": 0.45,
            "cpu_usage": 0.52,
            "voltage": 220.5,
        },
        "metadata": {"vendor": "ACME", "model": "X1000"},
    }


def test_health(client: SyncASGIClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["device"] == "cpu"


def test_predict_aging(client: SyncASGIClient) -> None:
    resp = client.post("/api/v1/predict/aging", json=make_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    result = data["result"]
    assert result["device_id"] == "dev-001"
    assert result["risk_level"] == "medium"
    assert len(result["contributors"]) == 3


def test_predict_fault(client: SyncASGIClient) -> None:
    resp = client.post("/api/v1/predict/fault", json=make_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    result = data["result"]
    assert result["device_id"] == "dev-001"
    assert result["risk_level"] == "high"
    assert result["prob_30d"] == pytest.approx(0.55)


def test_batch_predict(client: SyncASGIClient) -> None:
    payload = {"devices": [make_payload(), make_payload()]}
    resp = client.post("/api/v1/batch/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["failed_count"] == 0
    assert len(data["results"]) == 2


def test_predict_aging_returns_400(client: SyncASGIClient) -> None:
    try:
        set_engine(ValidationErrorEngine())
        resp = client.post("/api/v1/predict/aging", json=make_payload())
        assert resp.status_code == 400
        assert "指标缺失" in resp.json()["detail"]
    finally:
        set_engine(FakeEngine())


def test_predict_aging_returns_503_if_engine_missing(client: SyncASGIClient) -> None:
    try:
        set_engine(UnavailableEngine())
        resp = client.post("/api/v1/predict/aging", json=make_payload())
        assert resp.status_code == 503
    finally:
        set_engine(FakeEngine())


def test_predict_fault_returns_500_on_crash(client: SyncASGIClient) -> None:
    try:
        set_engine(CrashEngine())
        resp = client.post("/api/v1/predict/fault", json=make_payload())
        assert resp.status_code == 500
        assert "推理失败" in resp.json()["detail"]
    finally:
        set_engine(FakeEngine())
