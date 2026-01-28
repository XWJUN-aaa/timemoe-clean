"""数据预处理与指标计算工具（精简版）。"""
from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from app.utils.logger import logger


class DataProcessor:
    """围绕 TimeMoE 推理的轻量数据处理工具。"""

    DEFAULT_INPUT_LENGTH = 336
    DEFAULT_OUTPUT_LENGTH = 336
    HEALTH_WARN_THRESHOLD = 60.0
    HEALTH_CRITICAL_THRESHOLD = 40.0

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self.input_length = int(cfg.get("input_length", self.DEFAULT_INPUT_LENGTH))
        self.output_length = int(cfg.get("max_new_tokens", self.DEFAULT_OUTPUT_LENGTH))
        self.interval_hours = max(1, int(cfg.get("forecast_interval_hours", 24)))

    # ------------------------------------------------------------------ #
    # 序列构建与归一化
    # ------------------------------------------------------------------ #
    def prepare_sequence(
        self,
        metrics: Dict[str, Any],
        historical_data: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> Tuple[np.ndarray, float, float, np.ndarray]:
        """
        将历史数据转换为模型输入所需的归一化序列。

        Returns:
            normalized_sequence, mean, std, original_sequence
        """
        values = self._collect_series(metrics, historical_data)
        if not values:
            raise ValueError("缺少可用的历史温度序列")

        # 仅保留最近 input_length 条
        if len(values) >= self.input_length:
            series = np.array(values[-self.input_length :], dtype=np.float32)
        else:
            pad_value = values[-1]
            padded = values + [pad_value] * (self.input_length - len(values))
            series = np.array(padded, dtype=np.float32)

        mean = float(series.mean())
        std = float(series.std()) or 1.0
        normalized = (series - mean) / std
        return normalized, mean, std, series

    def _collect_series(
        self,
        metrics: Dict[str, Any],
        historical_data: Optional[Sequence[Dict[str, Any]]],
    ) -> List[float]:
        """优先使用历史数据中的温度指标，缺失时使用当前指标补全。"""
        series: List[Tuple[datetime, float]] = []
        if historical_data:
            for record in historical_data:
                ts = self._parse_timestamp(record.get("timestamp"))
                value = self._extract_primary_metric(record)
                if ts and value is not None:
                    series.append((ts, float(value)))

        # 若无历史数据，则使用当前指标构造常值序列
        if not series:
            current_value = self._extract_primary_metric(metrics)
            if current_value is None:
                return []
            return [float(current_value)]

        # 时间升序排序
        series.sort(key=lambda item: item[0])
        return [value for _, value in series]

    @staticmethod
    def _parse_timestamp(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            logger.debug("无法解析时间戳: %s", value)
            return None

    def build_forecast_timestamps(
        self,
        base_timestamp: Any,
        steps: int,
    ) -> List[datetime]:
        """
        以设备上报时间为起点生成未来预测时间轴。
        """
        steps = max(0, steps)
        parsed = self._parse_timestamp(base_timestamp)
        base = parsed or datetime.now(timezone.utc)
        interval = max(1, self.interval_hours)
        return [
            base + timedelta(hours=(idx + 1) * interval)
            for idx in range(steps)
        ]

    @staticmethod
    def _extract_primary_metric(record: Dict[str, Any]) -> Optional[float]:
        for key in (
            "temperature",
            "value",
            "metric",
            "measurement",
            "voltage",
        ):
            if key in record and record[key] is not None:
                try:
                    return float(record[key])
                except (TypeError, ValueError):
                    continue
        return None

    # ------------------------------------------------------------------ #
    # 指标计算
    # ------------------------------------------------------------------ #
    def compute_health_score(
        self, metrics: Dict[str, Any], temperature: Optional[float] = None
    ) -> float:
        """
        基于温度、电压、CPU 与内存使用率的启发式健康值 (0-100)。
        """
        temp = float(
            temperature
            if temperature is not None
            else metrics.get("temperature", 30.0)
        )
        raw_voltage = metrics.get("voltage", 220.0)
        try:
            voltage = float(raw_voltage)
        except (TypeError, ValueError):
            voltage = 220.0
        mem = float(metrics.get("memory_usage", 0.5))
        cpu = float(metrics.get("cpu_usage", 0.5))

        temp_penalty = max(0.0, temp - 35.0) * 2.0
        voltage_penalty = self._compute_voltage_penalty(voltage)
        mem_penalty = mem * 25.0
        cpu_penalty = cpu * 20.0

        score = 100.0 - (temp_penalty + voltage_penalty + mem_penalty + cpu_penalty)
        return float(np.clip(score, 0.0, 100.0))

    @staticmethod
    def _compute_voltage_penalty(voltage: float) -> float:
        """针对不同供电档位自适应计算电压惩罚。"""
        nominal = DataProcessor._infer_nominal_voltage(voltage)
        return max(0.0, abs(voltage - nominal) / 2.0)

    @staticmethod
    def _infer_nominal_voltage(voltage: float) -> float:
        """根据实测值推断最接近的供电额定电压。"""
        try:
            value = abs(float(voltage))
        except (TypeError, ValueError):
            return 220.0
        candidates = (12.0, 24.0, 48.0, 110.0, 220.0)
        closest = min(candidates, key=lambda target: abs(value - target))
        return closest

    def compute_health_series(
        self, future_temperatures: np.ndarray, metrics: Dict[str, Any]
    ) -> np.ndarray:
        """根据预测温度生成未来健康序列。"""
        return np.array(
            [
                self.compute_health_score(metrics, temperature=float(temp))
                for temp in future_temperatures
            ],
            dtype=np.float32,
        )

    def build_contributors(self, metrics: Dict[str, Any]) -> List[Tuple[str, float]]:
        """构造贡献因子列表，用于解释当前健康指数。"""
        weights = {
            "temperature": min(1.0, max(0.0, (metrics.get("temperature", 30.0) - 20) / 40)),
            "memory_usage": float(metrics.get("memory_usage", 0.0)),
            "cpu_usage": float(metrics.get("cpu_usage", 0.0)),
        }
        total = sum(weights.values()) or 1.0
        return [(name, value / total) for name, value in weights.items()]

    def estimate_time_to_threshold(
        self, health_series: np.ndarray, threshold: float
    ) -> Optional[int]:
        """
        估计健康指数首次低于阈值的时间（小时）。
        """
        indices = np.where(health_series < threshold)[0]
        if len(indices) == 0:
            return None
        return int(indices[0] * self.interval_hours)  # 序列按 interval_hours 计算

    def compute_risk_level(
        self, current_health: float, future_health: Optional[np.ndarray] = None
    ) -> str:
        """根据当前与未来健康值给出风险等级。"""
        min_future = (
            float(future_health.min()) if future_health is not None else current_health
        )
        score = min(current_health, min_future)
        if score < self.HEALTH_CRITICAL_THRESHOLD:
            return "critical"
        if score < self.HEALTH_WARN_THRESHOLD:
            return "high"
        if score < 80:
            return "medium"
        return "low"

    def compute_fault_prob_curve(self, future_temperatures: np.ndarray) -> np.ndarray:
        """
        为每个未来时间点计算单点故障概率。
        """
        return np.array(
            [self._sigmoid((float(temp) - 35.0) / 5.0) for temp in future_temperatures],
            dtype=np.float32,
        )

    def compute_fault_probabilities(
        self,
        future_temperatures: np.ndarray,
        prob_curve: Optional[np.ndarray] = None,
    ) -> Dict[str, float]:
        """基于未来温度曲线估计 7/14/30 天故障概率。"""
        curve = prob_curve
        if curve is None:
            curve = self.compute_fault_prob_curve(future_temperatures)
        horizon_map = {"prob_7d": 7, "prob_14d": 14, "prob_30d": 30}  # 单位: 天
        probs = {}
        for key, horizon in horizon_map.items():
            steps_needed = max(1, int(math.ceil((horizon * 24) / self.interval_hours)))
            window = curve[: min(len(curve), steps_needed)]
            if len(window) == 0:
                probs[key] = 0.0
            else:
                probs[key] = float(window.max())
        return probs

    @staticmethod
    def risk_from_probabilities(probs: Dict[str, float]) -> str:
        max_prob = max(probs.values(), default=0.0)
        if max_prob >= 0.7:
            return "critical"
        if max_prob >= 0.5:
            return "high"
        if max_prob >= 0.3:
            return "medium"
        return "low"

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    def build_fault_explanation(
        self, probs: Dict[str, float], future_temperatures: np.ndarray
    ) -> str:
        peak = float(future_temperatures.max()) if len(future_temperatures) else 0.0
        dominant = max(probs, key=probs.get)
        return (
            f"预测峰值温度约 {peak:.1f}°C，{dominant} 风险最高("
            f"{probs[dominant]*100:.1f}%)，建议关注散热与负载。"
        )
