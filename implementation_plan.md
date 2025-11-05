# TimeMoE 推理服务实施方案（与网管平台对接，普通服务版）

## 1. 目标与边界

- 以“普通 Python HTTP 服务”提供在线推理：两个核心场景（老化感知、故障趋势），通过 REST API 对外服务。
- 无状态：不引入数据库、Redis、消息队列；数据由网管平台（Spring Boot）聚合后以请求体传入。
- 设备：优先支持 CPU 推理，检测到 NPU 可自动使用；始终保证 CPU 兜底可用。
- 对接：网管平台负责鉴权、限流、持久化、告警；本服务专注推理与健康探针。

## 2. 技术架构（精简）

- Web/API: FastAPI + Uvicorn（去掉 Flask 混挂与 Celery）
- 推理: PyTorch + Transformers（TimeMoE），可选 torch_npu（Ascend）
- 可观测: 结构化日志、健康探针（/health），必要时暴露 Prometheus 指标
- 配置: 简化为模型与设备、日志、服务端口

## 3. 目录结构（精简）

```
timemoe_service/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI 主应用（预加载模型）
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py          # 路由与入参校验
│   │   └── models.py          # Pydantic 模型
│   ├── core/
│   │   ├── __init__.py
│   │   ├── timemoe_engine.py  # 推理引擎（CPU/NPU 兜底）
│   │   └── data_processor.py  # 轻量预处理
│   └── utils/
│       ├── __init__.py
│       ├── config.py          # 配置读取
│       └── logger.py          # 日志
├── config/
│   └── config.yaml            # 精简配置
├── data/
│   └── models/TimeMoE-50M/    # 模型文件
├── run_server.py               # 启动脚本（uvicorn）
└── requirements.txt
```

## 4. 配置（最小化示例）

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  workers: 2

model:
  path: "/root/projects/timemoe/timemoe_service/data/models/TimeMoE-50M"
  device: "cpu"      # 或 "npu:0"，不可用时自动降级到 cpu
  max_new_tokens: 336

logging:
  level: "INFO"
```

## 5. API 设计

- 健康检查: `GET /api/v1/health`
- 老化感知: `POST /api/v1/predict/aging`
- 故障趋势: `POST /api/v1/predict/fault`
- 可选批量: `POST /api/v1/batch/predict`

请求示例（aging/fault 通用）

```json
{
  "device_id": "dev-001",
  "timestamp": "2025-11-04T15:30:00Z",
  "metrics": {
    "temperature": 65.2,
    "memory_usage": 0.45,
    "cpu_usage": 0.52,
    "voltage": 220.5
  },
  "metadata": {"vendor": "ACME", "model": "X1000"}
}
```

响应示例（aging）

```json
{
  "success": true,
  "result": {
    "device_id": "dev-001",
    "health_index": 75.5,
    "tte_hours": 720,
    "rul_hours": 1440,
    "risk_level": "medium",
    "contributors": [
      {"metric": "temperature", "weight": 0.42},
      {"metric": "memory_usage", "weight": 0.31}
    ],
    "prediction_time": "2025-11-04T15:30:01Z"
  },
  "message": "预测成功"
}
```

错误码约定

- 400 参数不合法；503 模型未加载；500 内部错误
- 透传 `X-Request-ID` 便于链路追踪

## 6. 性能与容量

- 并发：`uvicorn --workers N`（CPU 可取 2-4，根据核数/延迟调优）
- 预热：启动时预加载模型并做一次空推理以减少首包延迟
- NPU 存在则使用；否则 CPU 兜底，延迟相对提升

## 7. 部署与运维

- 启动：`uvicorn app.main:fastapi_app --host 0.0.0.0 --port 8000 --workers 2`
- 仅内网暴露，由 Spring Boot 网关或 Nginx 做鉴权与限流（无需服务网格）
- 日志：JSON/结构化输出，带 `request_id`、`latency_ms`
- 健康探针：`/api/v1/health` 提供 liveness/readiness 信息

## 8. 测试策略（精简）

- 单测：数据预处理、推理引擎 CPU 兜底、入参校验
- 接口：FastAPI TestClient 覆盖 200/400/500/503 分支
- 压测：并发 50-200，看 95/99 分位延迟，调优 workers

## 9. 与网管平台对接

- Spring Boot 通过同步 REST 调用：`POST /api/v1/predict/aging|fault`，设置连接/读取超时与熔断
- 网管负责：数据聚合、鉴权、限流、持久化与告警
- 本服务：在线推理 + 健康检查；不落库
- 建议：统一 trace-id、超时（CPU 模式建议 3s 以内）、重试/熔断

### 附：Spring Boot WebClient 最小调用示例

```java
WebClient client = WebClient.builder()
    .baseUrl("http://timemoe-service:8000/api/v1")
    .build();

Map<String,Object> payload = Map.of(
    "device_id","dev-001",
    "timestamp", Instant.now().toString(),
    "metrics", Map.of("temperature",65.2,"memory_usage",0.45,"cpu_usage",0.52,"voltage",220.5)
);

String resp = client.post()
    .uri("/predict/aging")
    .contentType(MediaType.APPLICATION_JSON)
    .bodyValue(payload)
    .retrieve()
    .bodyToMono(String.class)
    .block(Duration.ofSeconds(3));
```

## 10. 代码轻量修复项（当前仓库）

- `app/api/routes.py` 顶部补充导入，修复 NameError
  - `from app.api.models import AgingResult, FaultTrendResult, Contributor`
- `app/core/timemoe_engine.py` 已含 CPU 兜底逻辑；配置 `model.device: cpu` 可强制 CPU
- Pydantic 命名空间告警：如需消除，可在模型 `model_config` 中设置 `protected_namespaces = ()`

---

# 原方案（保留，供参考）

## 1. 项目概述

基于 TimeMoE 大模型构建通信设备老化感知与故障趋势预测服务，使用 Flask + FastAPI 混合架构，在华为 Ascend NPU 上提供高性能推理能力。


## 2. 技术架构

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据采集层     │    │    算法服务层    │    │    展示告警层    │
│                │    │                │    │                │
│ 工业以太网交换机 │───▶│  TimeMoE 预测   │───▶│   Web 控制台    │
│ 温度/电压/内存   │    │  老化感知模块   │    │   告警推送      │
│ 设备元数据      │    │  故障趋势模块   │    │   API 接口      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 服务架构
- **Web 框架**: Flask (主服务) + FastAPI (API 路由)
- **推理引擎**: TimeMoE + torch_npu (Ascend NPU)
- **数据存储**: SQLite/PostgreSQL + Redis (缓存)
- **任务队列**: Celery + Redis (异步处理)
- **监控**: Prometheus + Grafana

## 3. 目录结构

```
timemoe_service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Flask 主应用
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py           # FastAPI 路由
│   │   └── models.py           # Pydantic 模型
│   ├── core/
│   │   ├── __init__.py
│   │   ├── timemoe_engine.py   # TimeMoE 推理引擎
│   │   ├── data_processor.py   # 数据预处理
│   │   └── predictor.py        # 预测逻辑
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py         # 数据库模型
│   │   └── schemas.py          # 数据结构
│   ├── services/
│   │   ├── __init__.py
│   │   ├── aging_service.py    # 老化感知服务
│   │   └── fault_service.py    # 故障趋势服务
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py           # 配置管理
│   │   └── logger.py           # 日志管理
│   └── static/                 # 静态文件
│       └── templates/          # HTML 模板
├── data/
│   ├── models/                 # 模型文件
│   └── datasets/               # 数据集
├── config/
│   ├── config.yaml             # 主配置
│   └── thresholds.yaml         # 告警阈值
├── scripts/
│   ├── train.py                # 训练脚本
│   └── deploy.py               # 部署脚本
├── tests/
├── requirements.txt
├── Dockerfile
└── README.md
```

## 4. 核心模块设计

### 4.1 TimeMoE 推理引擎 (core/timemoe_engine.py)

```python
class TimeMoEEngine:
    def __init__(self, model_path: str, device: str = "npu:0"):
        """初始化 TimeMoE 推理引擎"""
        
    def load_model(self) -> bool:
        """加载模型到 NPU"""
        
    def predict_sequence(self, input_data: np.ndarray) -> np.ndarray:
        """时序预测"""
        
    def predict_aging(self, device_metrics: Dict) -> Dict:
        """设备老化预测"""
        
    def predict_fault_trend(self, device_data: Dict) -> Dict:
        """故障趋势预测"""
```

### 4.2 数据处理器 (core/data_processor.py)

```python
class DataProcessor:
    def __init__(self, config: Dict):
        """数据预处理器"""
        
    def normalize_metrics(self, raw_data: Dict) -> np.ndarray:
        """指标标准化"""
        
    def create_time_windows(self, data: np.ndarray, 
                          input_len: int = 336, 
                          output_len: int = 336) -> Tuple:
        """创建时间窗口"""
        
    def extract_features(self, device_data: Dict) -> Dict:
        """特征工程"""
```

### 4.3 API 路由设计 (api/routes.py)

```python
# FastAPI 路由
@router.post("/predict/aging")
async def predict_aging(request: AgingRequest) -> AgingResponse:
    """设备老化感知预测"""
    
@router.post("/predict/fault")  
async def predict_fault(request: FaultRequest) -> FaultResponse:
    """故障趋势预测"""
    
@router.post("/batch/predict")
async def batch_predict(request: BatchRequest) -> BatchResponse:
    """批量预测"""
    
@router.get("/health")
async def health_check() -> Dict:
    """健康检查"""
```

## 5. 数据模型设计

### 5.1 输入数据结构

```python
# 设备指标数据
class DeviceMetrics(BaseModel):
    device_id: str
    timestamp: datetime
    voltage: float           # 电压 (V)
    temperature: float       # 温度 (°C)  
    memory_usage: float      # 内存使用率 (0-1)
    cpu_usage: float         # CPU使用率 (0-1)
    port_errors: int         # 端口错误数
    restart_count: int       # 重启次数
    uptime: int             # 运行时间 (秒)

# 设备元数据
class DeviceMetadata(BaseModel):
    device_id: str
    vendor: str             # 供应商
    model: str              # 型号
    batch: str              # 采购批次
    sw_version: str         # 软件版本
    hw_version: str         # 硬件版本
    region: str             # 区域
    install_date: datetime  # 安装日期
```

### 5.2 输出数据结构

```python
# 老化感知结果
class AgingResult(BaseModel):
    device_id: str
    health_index: float      # 健康指数 (0-100)
    tte_hours: Optional[int] # 阈值到达时间 (小时)
    rul_hours: Optional[int] # 剩余寿命 (小时)
    risk_level: str          # 风险等级: low/medium/high/critical
    contributors: List[Dict] # 贡献因子 [{"metric": "temperature", "weight": 0.42}]
    prediction_time: datetime

# 故障趋势结果  
class FaultTrendResult(BaseModel):
    device_id: str
    prob_7d: float          # 7天故障概率
    prob_14d: float         # 14天故障概率
    prob_30d: float         # 30天故障概率
    risk_level: str         # 风险等级
    explanation: str        # 预测解释
    prediction_time: datetime
```

## 6. 实施步骤

### 6.1 第一阶段：基础框架搭建 (1-2周)

**目标**: 完成基础服务框架和 TimeMoE 集成

**任务清单**:
- [ ] 创建项目目录结构
- [ ] 配置 Flask + FastAPI 混合框架
- [ ] 集成 TimeMoE 模型加载和 NPU 推理
- [ ] 实现基础的数据预处理模块
- [ ] 创建基础 API 接口框架
- [ ] 配置日志和监控

**关键代码**:
```bash
# 1. 创建项目结构
mkdir -p timemoe_service/{app/{api,core,models,services,utils,static/templates},data/{models,datasets},config,scripts,tests}

# 2. 安装依赖
pip install flask fastapi uvicorn torch_npu numpy pandas pydantic sqlalchemy redis celery

# 3. 复制 TimeMoE 模型
cp -r /root/projects/timemoe/TimeMoE-50M timemoe_service/data/models/
```

### 6.2 第二阶段：核心算法实现 (2-3周)

**目标**: 实现老化感知和故障趋势预测算法

**任务清单**:
- [ ] 实现设备老化感知算法
  - [ ] 健康指数 (HI) 计算
  - [ ] 阈值到达时间 (TTE) 预测  
  - [ ] 剩余寿命 (RUL) 估算
- [ ] 实现故障趋势预测算法
  - [ ] 多时间窗口故障概率预测
  - [ ] 风险等级分类
- [ ] 数据标准化和特征工程
- [ ] 模型推理优化 (批处理、缓存)

**核心算法伪代码**:
```python
def calculate_health_index(metrics: Dict) -> float:
    """计算健康指数"""
    # 1. 指标归一化
    normalized = normalize_metrics(metrics)
    
    # 2. 加权计算 HI
    weights = {"temperature": 0.3, "memory": 0.25, "voltage": 0.2, ...}
    hi = 100 - sum(weights[k] * normalized[k] for k in weights)
    
    return max(0, min(100, hi))

def predict_tte(sequence: np.ndarray, threshold: float) -> Optional[int]:
    """预测阈值到达时间"""
    # 1. TimeMoE 预测未来序列
    future_seq = timemoe_engine.predict_sequence(sequence)
    
    # 2. 计算未来健康指数
    future_hi = [calculate_health_index(step) for step in future_seq]
    
    # 3. 找到首次低于阈值的时间点
    for i, hi in enumerate(future_hi):
        if hi < threshold:
            return i * time_step_minutes
    
    return None  # 预测期内未达到阈值
```

### 6.3 第三阶段：API 接口开发 (1-2周)

**目标**: 完成 RESTful API 接口和文档

**任务清单**:
- [ ] 实现完整的 API 接口
  - [ ] `/predict/aging` - 老化感知
  - [ ] `/predict/fault` - 故障趋势
  - [ ] `/batch/predict` - 批量预测
  - [ ] `/health` - 健康检查
- [ ] 添加输入验证和错误处理
- [ ] 生成 API 文档 (Swagger)
- [ ] 实现接口鉴权和限流
- [ ] 添加接口测试用例

**API 示例**:
```python
@app.post("/api/v1/predict/aging")
async def predict_aging(request: AgingRequest):
    try:
        # 1. 数据验证
        validate_device_metrics(request.metrics)
        
        # 2. 数据预处理
        processed_data = data_processor.process(request.metrics)
        
        # 3. 模型预测
        result = timemoe_engine.predict_aging(processed_data)
        
        # 4. 结果后处理
        aging_result = AgingResult(
            device_id=request.device_id,
            health_index=result["hi"],
            tte_hours=result["tte"],
            rul_hours=result["rul"],
            risk_level=classify_risk_level(result["hi"]),
            contributors=result["contributors"],
            prediction_time=datetime.now()
        )
        
        return aging_result
        
    except Exception as e:
        logger.error(f"预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 6.4 第四阶段：告警和展示 (1-2周)

**目标**: 实现告警系统和 Web 控制台

**任务清单**:
- [ ] 实现告警规则引擎
  - [ ] 多级阈值告警
  - [ ] 告警去重和抑制
  - [ ] 告警推送 (邮件/短信/钉钉)
- [ ] 开发 Web 控制台
  - [ ] 设备状态看板
  - [ ] 历史趋势图表
  - [ ] 告警管理界面
- [ ] 数据存储和查询
- [ ] 性能监控和日志

**告警规则示例**:
```yaml
# config/thresholds.yaml
aging_thresholds:
  critical: 20    # HI < 20 严重告警
  high: 40        # HI < 40 高风险告警  
  medium: 60      # HI < 60 中风险告警
  
fault_thresholds:
  critical: 0.8   # 7天故障概率 > 80%
  high: 0.6       # 7天故障概率 > 60%
  medium: 0.4     # 7天故障概率 > 40%

alert_rules:
  - name: "设备老化严重告警"
    condition: "health_index < 20"
    severity: "critical"
    message: "设备 {device_id} 健康指数过低 ({health_index}), 请立即检查"
    
  - name: "故障风险告警" 
    condition: "prob_7d > 0.6"
    severity: "high"
    message: "设备 {device_id} 7天内故障概率较高 ({prob_7d:.1%})"
```

### 6.5 第五阶段：部署和优化 (1周)

**目标**: 生产环境部署和性能优化

**任务清单**:
- [ ] Docker 容器化部署
- [ ] 配置 Nginx 反向代理
- [ ] 设置 Gunicorn/Uvicorn 多进程
- [ ] 配置 Redis 缓存和会话
- [ ] 性能测试和优化
- [ ] 监控告警配置
- [ ] 文档和运维手册

**部署配置**:
```dockerfile
# Dockerfile
FROM python:3.10-slim

# 安装 Ascend 依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# 设置环境变量
ENV PYTHONPATH=/app
ENV ASCEND_TOOLKIT_PATH=/usr/local/Ascend/ascend-toolkit

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "app.main:app"]
```

## 7. 配置管理

### 7.1 主配置文件 (config/config.yaml)

```yaml
# 服务配置
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  debug: false

# 模型配置  
model:
  path: "/app/data/models/TimeMoE-50M"
  device: "npu:0"
  batch_size: 32
  input_length: 336
  output_length: 336

# 数据库配置
database:
  url: "sqlite:///data/timemoe.db"
  # url: "postgresql://user:pass@localhost/timemoe"
  
# Redis 配置
redis:
  host: "localhost"
  port: 6379
  db: 0
  
# 日志配置
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "/var/log/timemoe/app.log"
```

## 8. 测试策略

### 8.1 单元测试
- 数据预处理模块测试
- TimeMoE 推理引擎测试  
- 算法逻辑测试
- API 接口测试

### 8.2 集成测试
- 端到端预测流程测试
- 数据库集成测试
- 缓存集成测试

### 8.3 性能测试
- 单次预测响应时间 < 100ms
- 批量预测吞吐量 > 1000 req/s
- NPU 利用率 > 80%
- 内存使用 < 4GB

## 9. 监控和运维

### 9.1 关键指标监控
- API 响应时间和成功率
- NPU 利用率和温度
- 内存和 CPU 使用率
- 预测准确率 (MAE/MSE)
- 告警触发频率

### 9.2 日志管理
- 结构化日志 (JSON 格式)
- 日志轮转和归档
- 错误日志告警
- 审计日志记录

### 9.3 备份和恢复
- 模型文件备份
- 数据库定期备份
- 配置文件版本管理
- 灾难恢复预案

## 10. 风险和缓解措施

### 10.1 技术风险
- **NPU 故障**: 自动降级到 CPU 推理
- **模型性能下降**: 模型版本管理和回滚机制
- **数据质量问题**: 数据验证和清洗流程
- **并发性能**: 负载均衡和水平扩展

### 10.2 业务风险  
- **误报告警**: 阈值动态调整和历史校准
- **漏报风险**: 多模型集成和人工审核
- **数据安全**: 数据加密和访问控制
- **服务可用性**: 高可用部署和监控告警

## 11. 交付物清单

### 11.1 代码交付
- [ ] 完整源代码 (GitHub/GitLab)
- [ ] 单元测试和集成测试
- [ ] API 文档 (Swagger)
- [ ] 部署脚本和配置

### 11.2 文档交付
- [ ] 系统设计文档
- [ ] API 接口文档  
- [ ] 部署运维手册
- [ ] 用户使用手册

### 11.3 环境交付
- [ ] 开发环境搭建
- [ ] 测试环境部署
- [ ] 生产环境部署
- [ ] 监控告警配置

## 12. 时间计划

| 阶段 | 时间 | 主要任务 | 交付物 |
|------|------|----------|--------|
| 第1阶段 | 第1-2周 | 基础框架搭建 | 基础服务框架 |
| 第2阶段 | 第3-5周 | 核心算法实现 | 预测算法模块 |
| 第3阶段 | 第6-7周 | API接口开发 | RESTful API |
| 第4阶段 | 第8-9周 | 告警和展示 | Web控制台 |
| 第5阶段 | 第10周 | 部署和优化 | 生产环境 |

**总工期**: 10周 (约2.5个月)

## 13. 成功标准

### 13.1 功能指标
- ✅ 支持设备老化感知预测 (HI/TTE/RUL)
- ✅ 支持故障趋势预测 (多时间窗口概率)
- ✅ 提供完整的 RESTful API 接口
- ✅ 实现多级告警和 Web 展示
- ✅ 支持批量预测和实时预测

### 13.2 性能指标
- ✅ 单次预测响应时间 < 100ms
- ✅ 系统可用性 > 99.9%
- ✅ 预测准确率 MAE < 5%
- ✅ 支持 1000+ 设备并发监控

### 13.3 运维指标
- ✅ 完整的监控告警体系
- ✅ 自动化部署和扩展
- ✅ 完善的日志和审计
- ✅ 7x24 技术支持

---

**项目负责人**: [姓名]  
**创建时间**: 2025-11-04  
**最后更新**: 2025-11-04  
**版本**: v1.0
