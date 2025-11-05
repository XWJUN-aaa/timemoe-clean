#!/usr/bin/env python3
import torch
import torch_npu

print("="*60)
print("Environment Info")
print("="*60)
print(f"PyTorch version: {torch.__version__}")
print(f"torch_npu version: {torch_npu.__version__}")

print("\n" + "="*60)
print("NPU Device Info")
print("="*60)
npu_available = torch.npu.is_available()
print(f"NPU available: {npu_available}")

if npu_available:
    device_count = torch.npu.device_count()
    print(f"NPU device count: {device_count}")
    
    for i in range(device_count):
        print(f"\nDevice NPU:{i}")
        try:
            props = torch.npu.get_device_properties(i)
            print(f"  Name: {props.name}")
            print(f"  Total memory: {props.total_memory / 1024**3:.2f} GB")
        except Exception as e:
            print(f"  Cannot get properties: {e}")
    
    # Test NPU computation
    print("\n" + "="*60)
    print("NPU Computation Test")
    print("="*60)
    device = torch.device("npu:0")
    print(f"Using device: {device}")
    
    x = torch.randn(3, 3).to(device)
    y = torch.randn(3, 3).to(device)
    z = x + y
    
    print("SUCCESS: Tensor operation completed!")
    print(f"Result tensor device: {z.device}")
    print(f"Result shape: {z.shape}")
else:
    print("NPU is NOT available!")

print("\n" + "="*60)
print("Verification Complete")
print("="*60)
