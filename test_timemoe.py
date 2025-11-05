# import os

# os.environ.setdefault("ACCELERATE_DISABLE_NPU", "1")

# import torch
# from transformers import AutoModelForCausalLM

# print("=" * 60)
# print("Time-MoE 模型测试（NPU/CPU）")
# print("=" * 60)

# # 选择设备：优先 NPU，然后 CPU
# if hasattr(torch, "npu") and torch.npu.is_available():
#     device = torch.device("npu:0")
#     print("使用 NPU 推理")
# else:
#     device = torch.device("cpu")
#     print("使用 CPU 推理")
import os, torch
from transformers import AutoModelForCausalLM
try:
    import torch_npu  # 确保已安装
    use_npu = torch.npu.is_available()
except Exception:
    use_npu = False
device = torch.device("npu:0" if use_npu else "cpu")
print("使用 NPU 推理" if use_npu else "使用 CPU 推理")
print("npu.is_available:", use_npu)

print(f"PyTorch 版本: {torch.__version__}")
print(f"当前设备: {device}")

print("\n" + "=" * 60)
print("加载 Time-MoE-50M 模型...")
print("=" * 60)

try:
    model = AutoModelForCausalLM.from_pretrained(
        "./TimeMoE-50M",
        trust_remote_code=True,
        local_files_only=True,
    )
    model = model.to(device)
    model.eval()
    print("✓ 模型加载成功！")

    print("\n" + "=" * 60)
    print("生成预测...")
    print("=" * 60)

    context_length = 12
    seqs = torch.randn(2, context_length, device=device)
    print(f"输入序列形状: {seqs.shape}")
    print(f"输入序列示例:\n{seqs[0, :5].tolist()}")

    mean, std = seqs.mean(dim=-1, keepdim=True), seqs.std(dim=-1, keepdim=True)
    std[std == 0] = 1
    normed_seqs = (seqs - mean) / std

    prediction_length = 6
    print(f"\n预测长度: {prediction_length}")

    with torch.no_grad():
        output = model.generate(normed_seqs, max_new_tokens=prediction_length)

    normed_predictions = output[:, -prediction_length:]
    predictions = normed_predictions * std + mean

    print(f"输出序列形状: {output.shape}")
    print(f"预测结果形状: {predictions.shape}")
    print(f"预测结果示例:\n{predictions[0].tolist()}")

    print("\n" + "=" * 60)
    print("✓ 测试成功完成！")
    print("=" * 60)

except Exception as e:
    print(f"\n✗ 错误: {e}")
    import traceback
    traceback.print_exc()
