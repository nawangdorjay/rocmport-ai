# ROCm / AMD Developer Cloud Feedback

## What worked well

- The ROCm-enabled vLLM container gives developers a clear serving path for AMD Instinct GPUs.
- AMD Developer Cloud is well aligned with hackathon demos because developers can avoid local GPU setup.
- Qwen3-Coder-Next on AMD Instinct is a strong story for repo-level coding agents.

## Friction points to document during the live run

- Exact VM image, ROCm version, and Docker image should be easy to capture in benchmark logs.
- Users need obvious examples for replacing NVIDIA container flags and monitoring commands.
- More migration examples for common CUDA-first PyTorch repos would reduce onboarding time.

## Suggested product improvement

Publish a small official CUDA-to-ROCm migration checklist for PyTorch, vLLM, and Hugging Face inference projects, with copyable Docker commands for AMD Developer Cloud.
