"""
FastAPI 路由定义
"""
from fastapi import APIRouter, HTTPException, status
from typing import List

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

        prediction = engine.predict_aging(request.model_dump())
        contributor_items: List[Contributor] = [
            Contributor(**item) for item in prediction.get("contributors", [])
        ]
        result = AgingResult(**{**prediction, "contributors": contributor_items})

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

        prediction = engine.predict_fault_trend(request.model_dump())
        result = FaultTrendResult(**prediction)

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
