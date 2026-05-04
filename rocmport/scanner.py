from __future__ import annotations

import re
from pathlib import Path

from .ingest import iter_text_files
from .models import Finding


def scan_repository(root: Path) -> list[Finding]:
    files = iter_text_files(root)
    findings: list[Finding] = []
    has_dockerfile = False
    has_benchmark = False
    has_vllm_or_sglang = False

    for relative_path, text in files:
        path_lower = relative_path.lower()
        if Path(relative_path).name.lower().startswith("dockerfile"):
            has_dockerfile = True
        if "bench" in path_lower or "benchmark" in text.lower():
            has_benchmark = True
        if "vllm" in text.lower() or "sglang" in text.lower():
            has_vllm_or_sglang = True

        findings.extend(_scan_file(relative_path, text))

    if not has_dockerfile:
        findings.append(
            Finding(
                id="missing-dockerfile",
                category="deployment",
                severity="low",
                path=".",
                line=1,
                message="No Dockerfile was found for a reproducible ROCm deployment.",
                suggested_fix="Generate Dockerfile.rocm with ROCm/vLLM base image and AMD GPU device mounts.",
            )
        )

    if not has_benchmark:
        findings.append(
            Finding(
                id="missing-benchmark",
                category="benchmark",
                severity="low",
                path=".",
                line=1,
                message="No benchmark entrypoint was found.",
                suggested_fix="Add a reproducible latency, throughput, and memory collection command for AMD Developer Cloud.",
            )
        )

    if not has_vllm_or_sglang:
        findings.append(
            Finding(
                id="missing-serving-runbook",
                category="serving",
                severity="low",
                path=".",
                line=1,
                message="No vLLM or SGLang serving command was found.",
                suggested_fix="Generate a ROCm serving runbook using vllm/vllm-openai-rocm when LLM serving is needed.",
            )
        )

    return findings[:200]


def _scan_file(relative_path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    suffix = Path(relative_path).suffix.lower()
    file_name = Path(relative_path).name.lower()

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        lower = stripped.lower()

        if suffix in {".cu", ".cuh"} or _contains_cuda_kernel_api(stripped):
            findings.append(
                Finding(
                    id=f"cuda-kernel-{line_number}",
                    category="code",
                    severity="manual",
                    path=relative_path,
                    line=line_number,
                    message="CUDA kernel or CUDA runtime API usage requires manual HIP review.",
                    suggested_fix="Use HIPIFY or manually port CUDA C++ kernels; the MVP does not rewrite kernels.",
                    remediable=False,
                )
            )

        if re.search(r"\.cuda\s*\(", stripped):
            findings.append(
                Finding(
                    id=f"python-cuda-call-{line_number}",
                    category="code",
                    severity="high",
                    path=relative_path,
                    line=line_number,
                    message="PyTorch tensor or module is moved with a hardcoded .cuda() call.",
                    suggested_fix="Replace .cuda() with .to(_rocmport_device) and define a runtime device abstraction.",
                )
            )

        if re.search(r"torch\.device\(\s*['\"]cuda", stripped):
            findings.append(
                Finding(
                    id=f"torch-device-cuda-{line_number}",
                    category="code",
                    severity="high",
                    path=relative_path,
                    line=line_number,
                    message="torch.device is hardcoded to CUDA.",
                    suggested_fix="Use torch.device(\"cuda\" if torch.cuda.is_available() else \"cpu\"); ROCm PyTorch reports AMD GPUs through torch.cuda.",
                )
            )

        if re.search(r"\.to\(\s*['\"]cuda['\"]\s*\)", stripped):
            findings.append(
                Finding(
                    id=f"to-cuda-{line_number}",
                    category="code",
                    severity="high",
                    path=relative_path,
                    line=line_number,
                    message="Tensor or module transfer hardcodes the CUDA device string.",
                    suggested_fix="Replace .to(\"cuda\") with .to(_rocmport_device).",
                )
            )

        if "torch.cuda.is_available" in stripped and "rocm" not in lower:
            findings.append(
                Finding(
                    id=f"cuda-availability-check-{line_number}",
                    category="code",
                    severity="low",
                    path=relative_path,
                    line=line_number,
                    message="CUDA availability check may confuse ROCm users because PyTorch ROCm still uses the torch.cuda namespace.",
                    suggested_fix="Keep the API call but document that it covers AMD GPUs under ROCm PyTorch.",
                )
            )

        if "nvidia-smi" in lower:
            category = "benchmark" if "bench" in relative_path.lower() or "benchmark" in lower else "environment"
            findings.append(
                Finding(
                    id=f"nvidia-smi-{line_number}",
                    category=category,
                    severity="high",
                    path=relative_path,
                    line=line_number,
                    message="NVIDIA-specific GPU inspection command found.",
                    suggested_fix="Use rocm-smi for AMD GPU monitoring and benchmark metadata collection.",
                )
            )

        if re.search(r"\bNVIDIA_(VISIBLE_DEVICES|DRIVER_CAPABILITIES)\b", stripped):
            findings.append(
                Finding(
                    id=f"nvidia-env-{line_number}",
                    category="environment",
                    severity="medium",
                    path=relative_path,
                    line=line_number,
                    message="NVIDIA container environment variable found.",
                    suggested_fix="Use HIP_VISIBLE_DEVICES or ROCR_VISIBLE_DEVICES for AMD GPU targeting.",
                )
            )

        if re.search(r"\bCUDA_VISIBLE_DEVICES\b", stripped):
            findings.append(
                Finding(
                    id=f"cuda-visible-devices-{line_number}",
                    category="environment",
                    severity="medium",
                    path=relative_path,
                    line=line_number,
                    message="CUDA_VISIBLE_DEVICES is used for GPU selection.",
                    suggested_fix="Use HIP_VISIBLE_DEVICES or ROCR_VISIBLE_DEVICES for AMD GPU targeting.",
                )
            )

        if re.search(r"\bCUDA_(HOME|PATH)\b", stripped):
            findings.append(
                Finding(
                    id=f"cuda-path-env-{line_number}",
                    category="environment",
                    severity="medium",
                    path=relative_path,
                    line=line_number,
                    message="CUDA toolkit path environment variable found.",
                    suggested_fix="Remove CUDA toolkit path assumptions or replace with ROCm installation paths when required.",
                    remediable=False,
                )
            )

        if file_name.startswith("dockerfile") and re.search(r"^\s*FROM\s+nvidia/cuda", stripped, re.IGNORECASE):
            findings.append(
                Finding(
                    id=f"nvidia-docker-base-{line_number}",
                    category="environment",
                    severity="high",
                    path=relative_path,
                    line=line_number,
                    message="Dockerfile uses an NVIDIA CUDA base image.",
                    suggested_fix="Use vllm/vllm-openai-rocm:latest for vLLM serving or rocm/pytorch:latest for PyTorch workloads.",
                )
            )

        if "cudatoolkit" in lower or "cupy-cuda" in lower:
            findings.append(
                Finding(
                    id=f"cuda-package-{line_number}",
                    category="environment",
                    severity="medium",
                    path=relative_path,
                    line=line_number,
                    message="Dependency references a CUDA-specific package.",
                    suggested_fix="Replace CUDA-specific wheels with ROCm-compatible PyTorch or library builds.",
                    remediable=False,
                )
            )

        if "vllm serve" in lower or "vllm.entrypoints" in lower:
            findings.append(
                Finding(
                    id=f"vllm-rocm-runbook-{line_number}",
                    category="serving",
                    severity="low",
                    path=relative_path,
                    line=line_number,
                    message="vLLM serving command found without explicit ROCm container guidance.",
                    suggested_fix="Run vLLM inside vllm/vllm-openai-rocm with /dev/kfd, /dev/dri, host IPC, and video group access.",
                )
            )

        if "sglang.launch_server" in lower:
            findings.append(
                Finding(
                    id=f"sglang-rocm-runbook-{line_number}",
                    category="serving",
                    severity="low",
                    path=relative_path,
                    line=line_number,
                    message="SGLang launch command found without explicit ROCm deployment guidance.",
                    suggested_fix="Document ROCm-compatible serving image, AMD GPU device mounts, and fallback vLLM command.",
                )
            )

    return findings


def _contains_cuda_kernel_api(line: str) -> bool:
    return any(token in line for token in ("__global__", "cudaMalloc", "cudaMemcpy", "cudaFree"))
