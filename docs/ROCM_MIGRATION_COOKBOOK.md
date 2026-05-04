# ROCm Migration Cookbook

## PyTorch device handling

Use a runtime device abstraction instead of hardcoding `.cuda()` or `torch.device("cuda")` everywhere.

```python
import torch

# ROCm PyTorch exposes AMD GPUs through the torch.cuda namespace.
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)
inputs = inputs.to(device)
```

## GPU inspection

Replace NVIDIA-only commands with ROCm equivalents:

```bash
rocm-smi --showproductname --showmeminfo vram --showuse
```

## Containers

For vLLM serving on AMD GPUs, use the ROCm-enabled vLLM image:

```bash
docker pull vllm/vllm-openai-rocm:latest
```

Run with AMD GPU device access:

```bash
docker run --rm -it --device /dev/kfd --device /dev/dri --group-add video --ipc=host --network=host --security-opt seccomp=unconfined vllm/vllm-openai-rocm:latest
```

## Manual review cases

Manual migration is still required for CUDA C++ kernels, CUDA-only binary wheels, custom Triton kernels, and libraries that ship only CUDA builds.
