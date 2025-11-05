from __future__ import annotations

from fastapi import FastAPI

from app import fastapi_app
from app.api.routes import router, set_engine
from app.core.timemoe_engine import TimeMoEEngine
from app.utils.config import get_logging_config, get_model_config
from app.utils.logger import logger, setup_logger


def _configure_logging() -> None:
    cfg = get_logging_config()
    if not cfg:
        return
    setup_logger(
        level=cfg.get("level", "INFO"),
        log_file=cfg.get("file"),
        format_string=cfg.get("format"),
    )


def _init_engine() -> None:
    model_cfg = get_model_config()
    engine = TimeMoEEngine(
        model_path=model_cfg.get("path"),
        device=model_cfg.get("device"),
        device_priority=model_cfg.get("device_priority"),
    )
    if engine.load_model():
        set_engine(engine)
    else:
        logger.error("TimeMoE 引擎初始化失败，服务将降级运行")


@fastapi_app.on_event("startup")
async def _startup() -> None:
    _configure_logging()
    _init_engine()


def get_app() -> FastAPI:
    """供 uvicorn 引用的工厂方法。"""
    return fastapi_app


# 注册路由
fastapi_app.include_router(router)
