import torch
import sys

print("=" * 60)
print("环境信息")
print("=" * 60)
print(f"Python 版本: {sys.version}")
print(f"PyTorch 版本: {torch.__version__}")

# 检查 torch_npu
try:
    import torch_npu
    print(f"torch_npu 版本: {torch_npu.__version__}")
    npu_installed = True
except ImportError as e:
    print(f"torch_npu 未安装: {e}")
    npu_installed = False

print("\n" + "=" * 60)
print("NPU 设备信息")
print("=" * 60)

if npu_installed:
    try:
        npu_available = torch.npu.is_available()
        print(f"NPU 是否可用: {npu_available}")
        
        if npu_available:
            device_count = torch.npu.device_count()
            print(f"NPU 设备数量: {device_count}")
            
            for i in range(device_count):
                print(f"\n设备 {i}:")
                print(f"  名称: NPU:{i}")
                try:
                    props = torch.npu.get_device_properties(i)
                    print(f"  属性: {props}")
                except:
                    pass
            
            # 测试简单运算
            print("\n" + "=" * 60)
            print("NPU 计算测试")
            print("=" * 60)
            device = torch.device("npu:0")
            x = torch.randn(3, 3).to(device)
            y = torch.randn(3, 3).to(device)
            z = x + y
            print(f"测试张量运算成功！")
            print(f"设备: {z.device}")
        else:
            print("NPU 不可用，可能需要配置环境变量或驱动")
    except Exception as e:
        print(f"NPU 检查出错: {e}")
else:
    print("需要安装 torch_npu 才能使用昇腾 NPU")

print("\n" + "=" * 60)
