"""
数据预处理与风险评估逻辑的单元测试。
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict

import numpy as np
import pytest

from app.core.data_processor import DataProcessor


def _build_history() -> list[Dict[str, object]]:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        {"timestamp": (base + timedelta(hours=i)).isoformat(), "temperature": 35.0 + i}
        for i in range(2)
    ]


def test_prepare_sequence_pads_with_last_value() -> None:
    processor = DataProcessor({"input_length": 4, "max_new_tokens": 2})
    normalized, mean, std, series = processor.prepare_sequence(
        metrics={"temperature": 40.0},
        historical_data=_build_history(),
    )

    assert series.tolist() == pytest.approx([35.0, 36.0, 36.0, 36.0])
    assert normalized.shape == (4,)
    assert mean == pytest.approx(35.75, rel=1e-3)
    assert std > 0


def test_compute_health_score_bounds() -> None:
    processor = DataProcessor({})
    healthy = processor.compute_health_score(
        {"temperature": 28.0, "memory_usage": 0.1, "cpu_usage": 0.1, "voltage": 220.0}
    )
    hot_device = processor.compute_health_score(
        {"temperature": 75.0, "memory_usage": 0.9, "cpu_usage": 0.9, "voltage": 240.0}
    )

    assert 0.0 <= healthy <= 100.0
    assert 0.0 <= hot_device <= 100.0
    assert healthy > hot_device


def test_low_voltage_device_not_over_penalized() -> None:
    processor = DataProcessor({})
    low_voltage = processor.compute_health_score(
        {"temperature": 30.0, "memory_usage": 0.2, "cpu_usage": 0.2, "voltage": 24.5}
    )
    assert low_voltage > 40.0


def test_fault_probability_and_risk() -> None:
    processor = DataProcessor({})
    temps = np.linspace(35.0, 80.0, 336)
    probs = processor.compute_fault_probabilities(temps)
    assert set(probs.keys()) == {"prob_7d", "prob_14d", "prob_30d"}

    risk = processor.risk_from_probabilities(probs)
    assert risk in {"medium", "high", "critical"}


def test_estimate_time_to_threshold_detects_breach() -> None:
    processor = DataProcessor({"forecast_interval_hours": 1})
    series = np.array([90.0, 70.0, 55.0, 35.0], dtype=np.float32)
    tte = processor.estimate_time_to_threshold(
        series, processor.HEALTH_WARN_THRESHOLD
    )
    assert tte == 2
