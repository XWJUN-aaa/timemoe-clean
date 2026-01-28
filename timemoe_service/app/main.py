from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import fastapi_app
from app.api.routes import router, set_engine
from app.core.timemoe_engine import TimeMoEEngine
from app.utils.config import get_logging_config, get_model_config
from app.utils.logger import logger, setup_logger


def _configure_cors() -> None:
    """
    允许前端本地开发或同域静态站点访问。
    如需限制来源，请将 allow_origins 替换为具体域名。
    """
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _mount_static_frontend() -> None:
    """
    如 frontend 已构建 (frontend/dist)，则挂载静态文件方便一体化部署。
    """
    dist_dir = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if dist_dir.exists():
        fastapi_app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")
        logger.info("已挂载前端静态资源: %s", dist_dir)
    else:
        logger.info("未找到前端构建产物(frontend/dist)，跳过静态挂载")


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
    _configure_cors()
    _configure_logging()
    _init_engine()
    _mount_static_frontend()


def get_app() -> FastAPI:
    """供 uvicorn 引用的工厂方法。"""
    return fastapi_app


# 注册路由
fastapi_app.include_router(router)
