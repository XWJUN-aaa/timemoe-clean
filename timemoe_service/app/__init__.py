from __future__ import annotations

from fastapi import FastAPI

__version__ = "1.0.0"


def create_app() -> FastAPI:
    return FastAPI(
        title="TimeMoE 推理服务",
        description="提供老化感知与故障趋势预测的精简 REST API",
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )


fastapi_app = create_app()

