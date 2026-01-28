"""
API 数据模型 (Pydantic)
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ============== 请求模型 ==============

class DeviceMetrics(BaseModel):
    """设备指标"""
    voltage: Optional[float] = Field(None, description="电压 (V)")
    temperature: Optional[float] = Field(None, description="温度 (°C)")
    memory_usage: Optional[float] = Field(None, ge=0, le=1, description="内存使用率 (0-1)")
    cpu_usage: Optional[float] = Field(None, ge=0, le=1, description="CPU使用率 (0-1)")
    port_errors: Optional[int] = Field(None, ge=0, description="端口错误数")
    restart_count: Optional[int] = Field(None, ge=0, description="重启次数")
    uptime: Optional[int] = Field(None, ge=0, description="运行时间 (秒)")


class DeviceMetadata(BaseModel):
    """设备元数据"""
    vendor: Optional[str] = Field(None, description="供应商")
    model: Optional[str] = Field(None, description="型号")
    batch: Optional[str] = Field(None, description="采购批次")
    sw_version: Optional[str] = Field(None, description="软件版本")
    hw_version: Optional[str] = Field(None, description="硬件版本")
    region: Optional[str] = Field(None, description="区域")
    install_date: Optional[datetime] = Field(None, description="安装日期")


class AgingRequest(BaseModel):
    """老化感知预测请求"""
    device_id: str = Field(..., description="设备ID")
    timestamp: datetime = Field(..., description="时间戳")
    metrics: DeviceMetrics = Field(..., description="设备指标")
    metadata: Optional[DeviceMetadata] = Field(None, description="设备元数据")
    historical_data: Optional[List[Dict[str, Any]]] = Field(None, description="历史数据")


class FaultRequest(BaseModel):
    """故障趋势预测请求"""
    device_id: str = Field(..., description="设备ID")
    timestamp: datetime = Field(..., description="时间戳")
    metrics: DeviceMetrics = Field(..., description="设备指标")
    metadata: DeviceMetadata = Field(..., description="设备元数据")
    historical_data: Optional[List[Dict[str, Any]]] = Field(None, description="历史数据")


class BatchRequest(BaseModel):
    """批量预测请求"""
    devices: List[AgingRequest] = Field(..., description="设备列表")


# ============== 响应模型 ==============

class AgingForecastPoint(BaseModel):
    """老化预测序列点"""
    timestamp: datetime = Field(..., description="预测时间点")
    temperature: float = Field(..., description="预测温度 (°C)")
    health_index: float = Field(..., ge=0, le=100, description="预测健康指数 (0-100)")


class FaultForecastPoint(BaseModel):
    """故障预测序列点"""
    timestamp: datetime = Field(..., description="预测时间点")
    temperature: float = Field(..., description="预测温度 (°C)")
    fault_probability: float = Field(..., ge=0, le=1, description="该时刻故障概率 (0-1)")


class Contributor(BaseModel):
    """贡献因子"""
    metric: str = Field(..., description="指标名称")
    weight: float = Field(..., description="权重")


class AgingResult(BaseModel):
    """老化感知结果"""
    device_id: str
    health_index: float = Field(..., ge=0, le=100, description="健康指数 (0-100)")
    tte_hours: Optional[int] = Field(None, description="阈值到达时间 (小时)")
    rul_hours: Optional[int] = Field(None, description="剩余寿命 (小时)")
    risk_level: str = Field(..., description="风险等级: low/medium/high/critical")
    contributors: List[Contributor] = Field(default_factory=list, description="贡献因子")
    prediction_time: datetime = Field(default_factory=datetime.now, description="预测时间")
    forecast: List[AgingForecastPoint] = Field(default_factory=list, description="未来逐小时预测序列")
    forecast_interval_hours: int = Field(1, description="预测时间间隔 (小时)")
    forecast_horizon_hours: int = Field(0, description="预测总时长 (小时)")
    memory_usage: Optional[float] = Field(None, description="最新内存使用率 (%)")
    cpu_usage: Optional[float] = Field(None, description="最新CPU使用率 (%)")
    voltage: Optional[float] = Field(None, description="最新电压 (V)")
    temperature: Optional[float] = Field(None, description="最新温度 (°C)")


class FaultTrendResult(BaseModel):
    """故障趋势结果"""
    device_id: str
    prob_7d: float = Field(..., ge=0, le=1, description="7天故障概率")
    prob_14d: float = Field(..., ge=0, le=1, description="14天故障概率")
    prob_30d: float = Field(..., ge=0, le=1, description="30天故障概率")
    risk_level: str = Field(..., description="风险等级: low/medium/high/critical")
    explanation: str = Field(default="", description="预测解释")
    prediction_time: datetime = Field(default_factory=datetime.now, description="预测时间")
    forecast: List[FaultForecastPoint] = Field(default_factory=list, description="未来逐小时故障趋势")
    forecast_interval_hours: int = Field(1, description="预测时间间隔 (小时)")
    forecast_horizon_hours: int = Field(0, description="预测总时长 (小时)")
    memory_usage: Optional[float] = Field(None, description="最新内存使用率 (%)")
    cpu_usage: Optional[float] = Field(None, description="最新CPU使用率 (%)")
    voltage: Optional[float] = Field(None, description="最新电压 (V)")
    temperature: Optional[float] = Field(None, description="最新温度 (°C)")


class AgingResponse(BaseModel):
    """老化感知响应"""
    success: bool = Field(..., description="是否成功")
    result: Optional[AgingResult] = Field(None, description="预测结果")
    message: Optional[str] = Field(None, description="消息")


class FaultResponse(BaseModel):
    """故障趋势响应"""
    success: bool = Field(..., description="是否成功")
    result: Optional[FaultTrendResult] = Field(None, description="预测结果")
    message: Optional[str] = Field(None, description="消息")


class BatchResponse(BaseModel):
    """批量预测响应"""
    success: bool = Field(..., description="是否成功")
    results: List[AgingResult] = Field(default_factory=list, description="预测结果列表")
    failed_count: int = Field(0, description="失败数量")
    message: Optional[str] = Field(None, description="消息")


class HealthResponse(BaseModel):
    """健康检查响应"""
    model_config = ConfigDict(protected_namespaces=())

    status: str = Field(..., description="状态: healthy/unhealthy")
    version: str = Field(..., description="版本号")
    model_loaded: bool = Field(..., description="模型是否已加载")
    device: str = Field(..., description="推理设备")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
