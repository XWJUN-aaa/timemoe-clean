"""
FastAPI 路由定义
"""
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status

from app.api.models import (
    AgingRequest, AgingResponse, AgingResult,
    FaultRequest, FaultResponse, FaultTrendResult,
    BatchRequest, BatchResponse,
    HealthResponse, Contributor
)
from app.core.timemoe_engine import TimeMoEEngine
from app.utils.logger import logger
from app import __version__

# 创建路由器
router = APIRouter(prefix="/api/v1", tags=["prediction"])

# 全局引擎实例 (将在应用启动时初始化)
engine: TimeMoEEngine = None


def set_engine(e: TimeMoEEngine):
    """设置全局引擎实例"""
    global engine
    engine = e


def _get_processor_attr(attr: str, default: Any = None) -> Any:
    if not engine:
        return default
    processor = getattr(engine, "processor", None)
    return getattr(processor, attr, default) if processor else default


def _log_history_stats(
    request_name: str,
    device_id: str,
    historical_data: Optional[List[Dict[str, Any]]],
) -> int:
    history_len = len(historical_data or [])
    input_len = _get_processor_attr("input_length", 0)
    interval_hours = _get_processor_attr("interval_hours", 1)
    output_len = _get_processor_attr("output_length", 0)
    horizon_hours = interval_hours * output_len if output_len else 0

    logger.info(
        "%s: device_id=%s, 历史点数=%d, 模型窗口=%s, interval=%sh, horizon=%sh",
        request_name,
        device_id,
        history_len,
        input_len or "unknown",
        interval_hours,
        horizon_hours or "unknown",
    )
    if input_len and history_len < input_len:
        logger.warning(
            "%s: 历史点数(%d)低于 input_length(%d)，可能无法生成完整序列",
            request_name,
            history_len,
            input_len,
        )
    return history_len


def _log_prediction_payload(tag: str, payload: Any) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    try:
        serialized = json.dumps(payload, ensure_ascii=False, default=str)
    except TypeError:
        serialized = str(payload)
    logger.debug("[%s] %s", tag, serialized)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    健康检查接口
    """
    try:
        model_loaded = engine.is_available() if engine else False
        device = engine.device if engine else "unknown"
        
        return HealthResponse(
            status="healthy" if model_loaded else "unhealthy",
            version=__version__,
            model_loaded=model_loaded,
            device=device
        )
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return HealthResponse(
            status="unhealthy",
            version=__version__,
            model_loaded=False,
            device="unknown"
        )


@router.post("/predict/aging", response_model=AgingResponse)
async def predict_aging(request: AgingRequest):
    """
    设备老化感知预测接口
    
    Args:
        request: 老化预测请求
        
    Returns:
        老化预测结果
    """
    try:
        if not engine or not engine.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="模型未加载，服务不可用"
            )
        
        logger.info(f"收到老化预测请求: device_id={request.device_id}")
        _log_history_stats("老化预测请求", request.device_id, request.historical_data)

        prediction = engine.predict_aging(request.model_dump())
        _log_prediction_payload("aging.raw_prediction", prediction)
        contributor_items: List[Contributor] = [
            Contributor(**item) for item in prediction.get("contributors", [])
        ]
        result = AgingResult(**{**prediction, "contributors": contributor_items})
        _log_prediction_payload("aging.response_body", result.model_dump())

        return AgingResponse(
            success=True,
            result=result,
            message="预测成功"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"老化预测失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预测失败: {str(e)}"
        )


@router.post("/predict/fault", response_model=FaultResponse)
async def predict_fault(request: FaultRequest):
    """
    故障趋势预测接口
    
    Args:
        request: 故障趋势预测请求
        
    Returns:
        故障趋势预测结果
    """
    try:
        if not engine or not engine.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="模型未加载，服务不可用"
            )
        
        logger.info(f"收到故障趋势预测请求: device_id={request.device_id}")
        _log_history_stats("故障趋势请求", request.device_id, request.historical_data)

        prediction = engine.predict_fault_trend(request.model_dump())
        _log_prediction_payload("fault.raw_prediction", prediction)
        result = FaultTrendResult(**prediction)
        _log_prediction_payload("fault.response_body", result.model_dump())

        return FaultResponse(
            success=True,
            result=result,
            message="预测成功"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"故障趋势预测失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预测失败: {str(e)}"
        )


@router.post("/batch/predict", response_model=BatchResponse)
async def batch_predict(request: BatchRequest):
    """
    批量预测接口
    
    Args:
        request: 批量预测请求
        
    Returns:
        批量预测结果
    """
    try:
        if not engine or not engine.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="模型未加载，服务不可用"
            )
        
        logger.info(f"收到批量预测请求: {len(request.devices)} 个设备")
        
        results = []
        failed_count = 0
        
        # 逐个处理 (后续可优化为批量处理)
        for device_request in request.devices:
            try:
                # 调用单个预测接口
                aging_req = AgingRequest(**device_request.model_dump())
                response = await predict_aging(aging_req)
                
                if response.success and response.result:
                    results.append(response.result)
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"设备 {device_request.device_id} 预测失败: {e}")
                failed_count += 1
        
        return BatchResponse(
            success=True,
            results=results,
            failed_count=failed_count,
            message=f"批量预测完成: 成功 {len(results)} 个, 失败 {failed_count} 个"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量预测失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量预测失败: {str(e)}"
        )
