from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect a ROCmPort AI benchmark result shell.")
    parser.add_argument("--output", default="benchmark_result.json")
    parser.add_argument("--model", default="Qwen/Qwen3-Coder-Next-FP8")
    parser.add_argument("--throughput", type=float, default=None)
    parser.add_argument("--p50-latency-ms", type=float, default=None)
    parser.add_argument("--p95-latency-ms", type=float, default=None)
    parser.add_argument("--peak-vram-gb", type=float, default=None)
    args = parser.parse_args()

    result = {
        "verified": all(
            value is not None
            for value in (args.throughput, args.p50_latency_ms, args.p95_latency_ms, args.peak_vram_gb)
        ),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "hardware": _run(["rocm-smi", "--showproductname"]),
        "rocm_version": _run(["bash", "-lc", "rocminfo | head -40"]),
        "vllm_version": _run(["python", "-m", "vllm", "--version"]),
        "model": args.model,
        "prompt_config": {
            "input_tokens": 512,
            "output_tokens": 256,
            "concurrency": 8,
            "requests": 64,
        },
        "throughput_tokens_per_second": args.throughput,
        "p50_latency_ms": args.p50_latency_ms,
        "p95_latency_ms": args.p95_latency_ms,
        "peak_vram_gb": args.peak_vram_gb,
        "log_excerpt": "Attach vLLM benchmark output here before final submission.",
    }
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")


def _run(command: list[str]) -> str:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable: {exc}"
    output = (completed.stdout or completed.stderr).strip()
    return output[:2000] if output else f"command exited {completed.returncode} with no output"


if __name__ == "__main__":
    main()
