"""TimeMoE 推理引擎 (精简版)。"""
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, List

import os
import numpy as np
import torch

from app.utils.config import get_model_config
from app.utils.logger import logger
from app.core.data_processor import DataProcessor


class TimeMoEEngine:
    """TimeMoE 推理引擎"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        device_priority: Optional[Sequence[str]] = None,
    ):
        """
        初始化 TimeMoE 推理引擎

        Args:
            model_path: 模型路径
            device: 首选设备 (npu:0、cuda:0、cpu 等)
            device_priority: 兜底设备优先级列表
        """
        model_cfg = get_model_config()
        self.model_path = model_path or model_cfg.get("path", "")
        priority_cfg = model_cfg.get("device_priority", [])
        if isinstance(priority_cfg, str):
            priority_cfg = [priority_cfg]

        requested = device or model_cfg.get("device")
        merged_priority: List[str] = []
        if requested:
            merged_priority.append(str(requested))
        merged_priority.extend(device_priority or priority_cfg or [])
        merged_priority.append("cpu")  # 始终兜底
        self.device_priority = self._deduplicate_devices(merged_priority)

        self.device = None  # type: Optional[str]
        self.model = None
        self._initialized = False
        self.processor = DataProcessor(model_cfg)

    @staticmethod
    def _deduplicate_devices(candidates: Sequence[str]) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for candidate in candidates:
            if not candidate:
                continue
            normalized = str(candidate).strip()
            if normalized in seen:
                continue
            ordered.append(normalized)
            seen.add(normalized)
        return ordered

    def _resolve_device(self) -> str:
        """根据优先级选择可用设备。"""
        for candidate in self.device_priority:
            lower = candidate.lower()
            if lower.startswith("npu"):
                try:
                    import torch_npu  # type: ignore
                    if torch.npu.is_available():
                        logger.info("选择 NPU 设备: %s", candidate)
                        return candidate
                    logger.warning("NPU 设备不可用，尝试下一个候选: %s", candidate)
                except ImportError:
                    logger.warning("未安装 torch_npu，无法使用 %s，继续尝试兜底", candidate)
                    continue
            elif lower.startswith("cuda") or lower.startswith("gpu"):
                if torch.cuda.is_available():
                    logger.info("选择 CUDA 设备: %s", candidate)
                    return candidate
                logger.warning("CUDA 不可用，尝试下一个候选: %s", candidate)
            else:
                # CPU 或其他 torch 识别的设备字符串
                logger.info("选择设备: %s", candidate)
                return candidate
        logger.info("所有候选设备不可用，使用 CPU 兜底")
        return "cpu"

    def load_model(self) -> bool:
        """
        加载模型到指定设备
        
        Returns:
            是否加载成功
        """
        try:
            from transformers import AutoModelForCausalLM
            
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"模型路径不存在: {self.model_path}")
            
            self.device = self._resolve_device()
            logger.info("正在加载模型: %s", self.model_path)
            logger.info("目标设备: %s", self.device)
            
            # 加载模型
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                local_files_only=True,
            )
            
            # 迁移到指定设备
            if self.device and self.device.lower().startswith("npu"):
                if hasattr(torch, "npu"):
                    torch.npu.set_device(self.device)
                    self.model = self.model.to(self.device)
                else:
                    logger.warning("当前 PyTorch 版本未暴露 NPU 接口，切换到 CPU")
                    self.device = "cpu"
                    self.model = self.model.to("cpu")
            else:
                self.model = self.model.to(self.device or "cpu")
            self.model.eval()
            
            self._initialized = True
            logger.info("模型加载成功")
            return True
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def predict_sequence(
        self,
        input_data: np.ndarray,
        max_new_tokens: Optional[int] = None
    ) -> np.ndarray:
        """
        时序预测
        
        Args:
            input_data: 输入序列 [batch_size, input_length] 或 [input_length]
            max_new_tokens: 最大生成token数
            
        Returns:
            预测序列 [batch_size, input_length + max_new_tokens] 或 [input_length + max_new_tokens]
        """
        if not self._initialized:
            raise RuntimeError("模型未初始化，请先调用 load_model()")
        
        model_cfg = get_model_config()
        max_new_tokens = max_new_tokens or model_cfg.get("max_new_tokens", 336)
        
        # 转换为 torch tensor
        if isinstance(input_data, np.ndarray):
            input_tensor = torch.from_numpy(input_data).float()
        else:
            input_tensor = input_data
        
        # 确保是 2D [batch, seq]
        if input_tensor.dim() == 1:
            input_tensor = input_tensor.unsqueeze(0)
        
        # 移动到设备
        input_tensor = input_tensor.to(self.device)
        
        # 推理
        with torch.no_grad():
            output = self.model.generate(
                input_tensor,
                max_new_tokens=max_new_tokens
            )
        
        # 返回 numpy 数组
        return output.cpu().numpy()
    
    def predict_aging(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        设备老化预测
        
        Args:
            payload: 请求体字典
            
        Returns:
            预测结果字典
        """
        if not self._initialized:
            raise RuntimeError("模型未初始化")

        metrics = payload.get("metrics", {})
        history = payload.get("historical_data")

        normalized, mean, std, series = self.processor.prepare_sequence(
            metrics=metrics, historical_data=history
        )

        model_cfg = get_model_config()
        max_tokens = int(model_cfg.get("max_new_tokens", self.processor.output_length))

        generated = self.predict_sequence(normalized, max_new_tokens=max_tokens)
        generated = generated[:, -max_tokens:]
        future_temperatures = (generated * std) + mean  # 反归一化
        future_temperatures = future_temperatures.flatten()

        current_health = self.processor.compute_health_score(metrics, temperature=float(series[-1]))
        future_health = self.processor.compute_health_series(future_temperatures, metrics)

        tte = self.processor.estimate_time_to_threshold(
            future_health, self.processor.HEALTH_WARN_THRESHOLD
        )
        rul = self.processor.estimate_time_to_threshold(
            future_health, self.processor.HEALTH_CRITICAL_THRESHOLD
        )

        risk_level = self.processor.compute_risk_level(current_health, future_health)
        contributors = [
            {"metric": name, "weight": round(weight, 4)}
            for name, weight in self.processor.build_contributors(metrics)
        ]

        return {
            "device_id": payload.get("device_id"),
            "health_index": round(current_health, 2),
            "tte_hours": tte,
            "rul_hours": rul,
            "risk_level": risk_level,
            "contributors": contributors,
        }
    
    def predict_fault_trend(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        故障趋势预测
        
        Args:
            payload: 请求体字典
            
        Returns:
            预测结果字典
        """
        if not self._initialized:
            raise RuntimeError("模型未初始化")

        metrics = payload.get("metrics", {})
        history = payload.get("historical_data")

        normalized, mean, std, _ = self.processor.prepare_sequence(
            metrics=metrics, historical_data=history
        )

        model_cfg = get_model_config()
        max_tokens = int(model_cfg.get("max_new_tokens", self.processor.output_length))

        generated = self.predict_sequence(normalized, max_new_tokens=max_tokens)
        generated = generated[:, -max_tokens:]
        future_temperatures = (generated * std) + mean
        future_temperatures = future_temperatures.flatten()

        probs = self.processor.compute_fault_probabilities(future_temperatures)
        risk_level = self.processor.risk_from_probabilities(probs)
        explanation = self.processor.build_fault_explanation(probs, future_temperatures)

        return {
            "device_id": payload.get("device_id"),
            **{key: round(value, 4) for key, value in probs.items()},
            "risk_level": risk_level,
            "explanation": explanation,
        }
    
    def is_available(self) -> bool:
        """检查模型是否可用"""
        return self._initialized and self.model is not None
