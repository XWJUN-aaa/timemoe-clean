"""
精简配置加载工具。
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml


CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.yaml"


@lru_cache()
def load_config(config_path: str | os.PathLike[str] | None = None) -> Dict[str, Any]:
    """
    加载 YAML 配置。
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def get_server_config() -> Dict[str, Any]:
    """获取 server 配置块。"""
    return load_config().get("server", {})


def get_model_config() -> Dict[str, Any]:
    """获取 model 配置块。"""
    return load_config().get("model", {})


def get_logging_config() -> Dict[str, Any]:
    """获取 logging 配置块。"""
    return load_config().get("logging", {})

