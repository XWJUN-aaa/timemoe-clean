import os
import sys

# Set Ascend environment
os.environ['LD_LIBRARY_PATH'] = '/usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64/common:/usr/local/Ascend/driver/lib64/driver:' + os.environ.get('LD_LIBRARY_PATH', '')
os.environ['ASCEND_TOOLKIT_HOME'] = '/usr/local/Ascend/ascend-toolkit/latest'
os.environ['PYTHONPATH'] = '/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:' + os.environ.get('PYTHONPATH', '')

import torch
import torch_npu

print("="*60)
print("Environment Check")
print("="*60)
print(f"PyTorch: {torch.__version__}")
print(f"torch_npu: {torch_npu.__version__}")
print(f"LD_LIBRARY_PATH set: {'Ascend' in os.environ.get('LD_LIBRARY_PATH', '')}")
print(f"ASCEND_TOOLKIT_HOME: {os.environ.get('ASCEND_TOOLKIT_HOME', 'Not set')}")

print("\n" + "="*60)
print("NPU Test")
print("="*60)
try:
    npu_available = torch.npu.is_available()
    print(f"NPU available: {npu_available}")
    
    if npu_available:
        count = torch.npu.device_count()
        print(f"NPU count: {count}")
        
        # Simple computation test
        device = torch.device("npu:0")
        x = torch.randn(2, 3).to(device)
        y = torch.randn(2, 3).to(device)
        z = x + y
        print(f"Computation test: SUCCESS")
        print(f"Result device: {z.device}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("="*60)
