#!/usr/bin/env bash
set -euo pipefail

export CUDA_VISIBLE_DEVICES=0
nvidia-smi
vllm serve Qwen/Qwen2.5-0.5B-Instruct --tensor-parallel-size 1
