# TimeMoE 预测服务

基于 TimeMoE 大模型的通信设备老化感知与故障趋势预测服务。

## 功能特性

- 🔥 **高性能推理**: 基于华为 Ascend NPU 的加速推理
- 📊 **设备老化感知**: 健康指数(HI)、阈值到达时间(TTE)、剩余寿命(RUL)预测
- ⚠️ **故障趋势预测**: 多时间窗口故障概率预测
- 🚀 **RESTful API**: 完整的 FastAPI 接口文档
- 📈 **实时监控**: 设备状态和告警管理

## 快速开始

### 1. 环境准备

```bash
# 激活 conda 环境
conda activate timemoe

# 安装依赖
cd timemoe_service
pip install -r requirements.txt
```

### 2. 配置模型

确保 TimeMoE 模型已放置在 `data/models/TimeMoE-50M/` 目录下。

### 3. 运行服务

```bash
# 开发模式
python -m app.main

# 或使用 uvicorn
uvicorn app.main:fastapi_app --host 0.0.0.0 --port 8000
```

### 4. 访问 API 文档

打开浏览器访问: http://localhost:8000/api/docs

## API 接口

### 健康检查
```bash
GET /api/v1/health
```

### 设备老化感知预测
```bash
POST /api/v1/predict/aging
Content-Type: application/json

{
  "device_id": "sw-001",
  "timestamp": "2025-11-04T13:50:00Z",
  "metrics": {
    "voltage": 48.1,
    "temperature": 63.2,
    "memory_usage": 0.78
  }
}
```

### 故障趋势预测
```bash
POST /api/v1/predict/fault
Content-Type: application/json

{
  "device_id": "sw-001",
  "timestamp": "2025-11-04T13:50:00Z",
  "metrics": {
    "voltage": 48.1,
    "temperature": 63.2
  },
  "metadata": {
    "vendor": "V1",
    "model": "M100",
    "region": "NJC"
  }
}
```

## 项目结构

```
timemoe_service/
├── app/                    # 应用代码
│   ├── api/               # API 路由和模型
│   ├── core/              # 核心模块 (TimeMoE引擎)
│   ├── services/          # 业务服务
│   └── utils/             # 工具模块
├── config/                # 配置文件
├── data/                  # 数据和模型
└── tests/                 # 测试代码
```

## 开发指南

详细开发指南请参考 [implementation_plan.md](../implementation_plan.md)

## 许可证

[许可证信息]

