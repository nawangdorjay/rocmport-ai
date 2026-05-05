"""
Throughput and latency benchmark for Qwen inference.
Contains NVIDIA-specific monitoring commands that ROCmPort will flag.
"""

import os
import subprocess
import time
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"  # should → HIP_VISIBLE_DEVICES

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
PROMPT = "Explain the difference between CUDA and ROCm in three sentences."
N_RUNS = 20
MAX_NEW_TOKENS = 128


def gpu_info() -> dict:
    """Collect GPU info — uses nvidia-smi which must become rocm-smi."""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=False,
    )
    return {"raw": result.stdout.strip()}


def run_benchmark():
    # Collect hardware info before loading model
    hw = gpu_info()
    print("GPU info:", hw)

    device = torch.device("cuda")          # hardcoded CUDA device
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID).cuda()   # .cuda()
    model.eval()

    inputs = tokenizer(PROMPT, return_tensors="pt").to("cuda")       # .to("cuda")

    # Warm-up
    with torch.no_grad():
        model.generate(**inputs, max_new_tokens=8)

    latencies = []
    token_counts = []

    for _ in range(N_RUNS):
        t0 = time.perf_counter()
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS)
        latencies.append((time.perf_counter() - t0) * 1000)
        token_counts.append(out.shape[-1] - inputs["input_ids"].shape[-1])

    p50 = sorted(latencies)[N_RUNS // 2]
    p95 = sorted(latencies)[int(N_RUNS * 0.95)]
    avg_tokens = sum(token_counts) / len(token_counts)
    throughput = avg_tokens / (sum(latencies) / len(latencies) / 1000)

    # Check VRAM
    vram_gb = torch.cuda.memory_reserved() / (1024 ** 3)

    result = {
        "hardware": hw,
        "model": MODEL_ID,
        "n_runs": N_RUNS,
        "p50_latency_ms": round(p50, 2),
        "p95_latency_ms": round(p95, 2),
        "throughput_tokens_per_second": round(throughput, 2),
        "peak_vram_gb": round(vram_gb, 2),
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run_benchmark()
