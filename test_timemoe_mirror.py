#!/usr/bin/env python3
"""
使用 NPU 测试 Time-MoE 模型的脚本（使用 ETTh1 无训练直接验证）
"""
import os
import json
from pathlib import Path
import numpy as np
import torch
from transformers import AutoModelForCausalLM

# 设置 Hugging Face 镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

print("="*60)
print("Time-MoE 模型测试 (NPU 版本)")
print("="*60)

# 检查 PyTorch 和设备
print(f"\nPyTorch 版本: {torch.__version__}")

# 尝试导入 torch_npu
try:
    import torch_npu
    print(f"torch_npu 版本: {torch_npu.__version__}")
    npu_available = torch.npu.is_available()
    print(f"NPU 可用: {npu_available}")
    
    if npu_available:
        npu_count = torch.npu.device_count()
        print(f"NPU 设备数量: {npu_count}")
        device = torch.device("npu:0")
        print(f"使用设备: {device}")
    else:
        print("⚠️ NPU 不可用（可能是无卡开机状态）")
        print("将使用 CPU 进行推理")
        device = torch.device("cpu")
except ImportError:
    print("⚠️ 未安装 torch_npu，使用 CPU")
    device = torch.device("cpu")
    device_map = "cpu"

print("\n" + "="*60)
print("加载 Time-MoE-50M 模型...")
print("模型路径: /root/projects/timemoe/TimeMoE-50M")
print("="*60)

try:
    # 加载模型后再显式迁移到目标设备（避免 auto 误回落到 CPU）
    model = AutoModelForCausalLM.from_pretrained(
        '/root/projects/timemoe/TimeMoE-50M',
        trust_remote_code=True,
        local_files_only=True,
    )
    model = model.to(device)
    print("✓ 模型加载成功！")
    print(f"模型设备: {next(model.parameters()).device}")

    # ============== 使用 ETTh1 数据集进行无训练验证 ==============
    print("\n" + "="*60)
    print("生成预测 (ETTh1)...")
    print("="*60)

    ds_root = Path('/root/projects/timemoe/data/TimeSeriesDatasets/ETTh1')
    desc = json.loads((ds_root / 'desc.json').read_text())
    T, N, F = desc['shape']
    inp_len = int(desc['regular_settings']['INPUT_LEN'])
    out_len = int(desc['regular_settings']['OUTPUT_LEN'])
    ratios = desc['regular_settings']['TRAIN_VAL_TEST_RATIO']
    t_train = int(T * float(ratios[0]))
    t_val = int(T * (float(ratios[0]) + float(ratios[1])))

    raw = np.fromfile(ds_root / 'data.dat', dtype=np.float32).reshape(T, N, F)
    target = raw[..., 0]  # [T, N]

    # 按通道（节点）在训练段做标准化
    train_slice = target[:t_train]  # [t_train, N]
    mean = train_slice.mean(axis=0, keepdims=True)
    std = train_slice.std(axis=0, keepdims=True)
    std[std == 0] = 1.0
    normed = (target - mean) / std  # [T, N]

    # 在测试段中间挑一条样本，节点取 0
    start = max(t_val, T - (inp_len + out_len) - 1)
    start = min(start, T - (inp_len + out_len) - 1)
    node_idx = 0
    x_in = normed[start:start+inp_len, node_idx]          # [inp_len]
    y_true = target[start+inp_len:start+inp_len+out_len, node_idx]  # 未归一化真值

    # 构造 batch=1 的输入，迁移到模型设备
    x = torch.from_numpy(x_in[None, :]).to(torch.float32).to(device)
    print(f"输入序列形状: {tuple(x.shape)}  节点: {node_idx}  起始t: {start}")
    print(f"输入数据设备: {x.device}")
    print(f"预测长度: {out_len}")

    with torch.no_grad():
        out = model.generate(x, max_new_tokens=out_len)
    pred_norm = out[:, -out_len:]  # [1, out_len]

    # 反归一化
    node_mean = float(mean[0, node_idx])
    node_std = float(std[0, node_idx])
    y_pred = pred_norm.cpu().numpy()[0] * node_std + node_mean

    # 简单指标
    mae = float(np.mean(np.abs(y_pred - y_true)))
    mse = float(np.mean((y_pred - y_true) ** 2))

    print(f"输出序列形状: {tuple(out.shape)}")
    print(f"预测结果形状: {(1, out_len)}")
    print(f"样例预测: {y_pred[:10].tolist()}")
    print(f"样例真值: {y_true[:10].tolist()}")
    print(f"MAE: {mae:.6f}  MSE: {mse:.6f}")
    
    print("\n" + "="*60)
    print("✓ 测试成功完成！")
    print("="*60)
    
except Exception as e:
    print(f"\n✗ 错误: {e}")
    import traceback
    traceback.print_exc()
    
    print("\n" + "="*60)
    print("解决方案：")
    print("="*60)
    print("1. 如果网络问题，请手动下载模型：")
    print("   https://hf-mirror.com/Maple728/TimeMoE-50M")
    print("2. 或检查网络连接")
    print("3. 或使用本地已有的模型文件")


