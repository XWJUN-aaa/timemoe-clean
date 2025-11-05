"""
TimeMoE 推理引擎兜底策略（NPU/CPU）的测试。
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence
import types
import sys

import pytest

from app.core.timemoe_engine import TimeMoEEngine


class DummyEngine(TimeMoEEngine):
    """避免实际加载模型的派生类。"""

    def __init__(self, device_priority: Sequence[str]):
        super().__init__(
            model_path=str(Path.cwd()),  # 仅用于初始化，不会访问
            device_priority=device_priority,
        )


def test_resolve_device_prefers_npu_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    # 忽略配置中的默认 device，确保以测试提供的优先级为准
    import app.core.timemoe_engine as eng
    monkeypatch.setattr(eng, "get_model_config", lambda: {}, raising=False)
    engine = DummyEngine(["npu:0", "cpu"])

    # 注入一个假的 torch_npu 模块以避免 ImportError
    sys.modules["torch_npu"] = types.ModuleType("torch_npu")
    # 通过对象方式 monkeypatch，避免 dotted-path 导入失败
    monkeypatch.setattr(
        eng.torch, "npu", types.SimpleNamespace(is_available=lambda: True), raising=False
    )

    resolved = engine._resolve_device()
    assert resolved == "npu:0"


def test_resolve_device_falls_back_to_cpu_when_npu_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.core.timemoe_engine as eng
    monkeypatch.setattr(eng, "get_model_config", lambda: {}, raising=False)
    engine = DummyEngine(["npu:0", "cpu"])

    # 注入模块，但返回不可用
    sys.modules["torch_npu"] = types.ModuleType("torch_npu")
    monkeypatch.setattr(
        eng.torch, "npu", types.SimpleNamespace(is_available=lambda: False), raising=False
    )

    resolved = engine._resolve_device()
    assert resolved == "cpu"
