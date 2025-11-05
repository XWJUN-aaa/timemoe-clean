#!/bin/bash
# Time-MoE 模型运行脚本 (NPU 版本)

echo "=========================================="
echo "Time-MoE NPU 运行脚本"
echo "=========================================="

# 激活 conda 环境
source /root/miniconda3/etc/profile.d/conda.sh
conda activate timemoe

# 显示环境信息
echo "当前环境: $(which python)"
echo "Python 版本: $(python --version)"

# 运行模型
echo ""
echo "运行 Time-MoE 模型..."
echo ""

python test_timemoe_mirror.py

echo ""
echo "=========================================="
echo "完成！"
echo "=========================================="


