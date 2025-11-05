#!/usr/bin/env python3
"""
服务启动脚本
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置 Ascend 环境变量 (如果存在)
ascend_env_script = "/usr/local/Ascend/ascend-toolkit/set_env.sh"
if os.path.exists(ascend_env_script):
    import subprocess
    try:
        result = subprocess.run(
            f"source {ascend_env_script} && env",
            shell=True,
            capture_output=True,
            text=True,
            executable="/bin/bash"
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✓ Ascend 环境变量已加载")
    except Exception as e:
        print(f"⚠ 加载 Ascend 环境变量失败: {e}")

if __name__ == "__main__":
    import uvicorn
    from app.utils.config import get_server_config

    try:
        server_config = get_server_config()

        host = server_config.get("host", "0.0.0.0")
        port = server_config.get("port", 8000)

        print("=" * 60)
        print("TimeMoE 预测服务")
        print("=" * 60)
        print(f"服务地址: http://{host}:{port}")
        print(f"API 文档: http://{host}:{port}/api/docs")
        print(f"健康检查: http://{host}:{port}/api/v1/health")
        print("=" * 60)
        
        # 启动服务
        uvicorn.run(
            "app.main:fastapi_app",
            host=host,
            port=port,
            log_level="info",
            reload=False
        )
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

