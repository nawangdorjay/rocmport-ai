from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from .models import CATEGORY_LABELS, MigrationBundle


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def generate_rocm_dockerfile(repo_name: str) -> str:
    return f"""FROM vllm/vllm-openai-rocm:latest

WORKDIR /workspace/{repo_name}
COPY . /workspace/{repo_name}

RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

ENV HIP_VISIBLE_DEVICES=0
ENV PYTORCH_HIP_ALLOC_CONF=expandable_segments:True

CMD ["python", "-c", "import torch; print('torch', torch.__version__); print('rocm_gpu_available', torch.cuda.is_available())"]
"""


def generate_runbook(repo_name: str) -> str:
    return f"""# AMD Developer Cloud Runbook

This runbook validates `{repo_name}` on AMD Developer Cloud without executing untrusted code inside the ROCmPort AI Space.

## 1. Create an AMD GPU VM

Use an AMD Developer Cloud VM with an AMD Instinct GPU and ROCm-ready Docker support.

## 2. Build the ROCm container

```bash
docker build -f Dockerfile.rocm -t rocmport-{repo_name.lower()} .
```

## 3. Run a smoke check

```bash
docker run --rm -it \\
  --device /dev/kfd \\
  --device /dev/dri \\
  --group-add video \\
  --ipc=host \\
  --network=host \\
  --security-opt seccomp=unconfined \\
  rocmport-{repo_name.lower()}
```

## 4. Run vLLM on ROCm

```bash
docker run --rm -it \\
  --device /dev/kfd \\
  --device /dev/dri \\
  --group-add video \\
  --ipc=host \\
  --network=host \\
  --security-opt seccomp=unconfined \\
  -v "$PWD:/workspace/{repo_name}" \\
  vllm/vllm-openai-rocm:latest \\
  vllm serve Qwen/Qwen3-Coder-Next-FP8 --tensor-parallel-size 1
```

## 5. Capture benchmark metadata

```bash
rocm-smi --showproductname --showmeminfo vram --showuse
python scripts/collect_benchmark_result.py --output benchmark_result.json
```

Replace `data/benchmark_result.json` with the captured result before final submission.
"""


def load_benchmark() -> dict[str, Any]:
    path = PROJECT_ROOT / "data" / "benchmark_result.json"
    if not path.exists():
        return {"verified": False, "status": "missing"}
    return json.loads(path.read_text(encoding="utf-8"))


def generate_report(bundle: MigrationBundle, qwen_section: str | None = None) -> str:
    lines = [
        f"# ROCmPort AI Migration Report: {bundle.repo_name}",
        "",
        "## AMD Readiness Score",
        "",
        f"- Before deterministic fixes: {bundle.before_score.total}/100",
        f"- Migration package generated: {bundle.after_score.total}/100",
        "- This score means ROCm migration artifacts were generated and are ready for AMD Developer Cloud validation; it is not a production certification.",
        "",
        "| Category | Before | Migration package |",
        "| --- | ---: | ---: |",
    ]
    for category, label in CATEGORY_LABELS.items():
        lines.append(
            f"| {label} | {bundle.before_score.categories[category]} | {bundle.after_score.categories[category]} |"
        )

    lines.extend(["", "## Findings", ""])
    if not bundle.findings:
        lines.append("No ROCm migration blockers were found by the MVP scanner.")
    else:
        lines.extend(["| Severity | Category | Location | Finding | Suggested fix |", "| --- | --- | --- | --- | --- |"])
        for finding in bundle.findings:
            lines.append(
                f"| {finding.severity} | {CATEGORY_LABELS.get(finding.category, finding.category)} | "
                f"`{finding.path}:{finding.line}` | {finding.message} | {finding.suggested_fix} |"
            )

    lines.extend(
        [
            "",
            "## Generated Artifacts",
            "",
            "- `rocm_patch.diff` contains deterministic MVP fixes.",
            "- `Dockerfile.rocm` uses the ROCm-enabled vLLM container.",
            "- `amd_developer_cloud_runbook.md` documents the validation path.",
            "- `benchmark_result.json` records the AMD benchmark schema and status.",
            "",
            "## Qwen Agent Notes",
            "",
            qwen_section
            or "Qwen endpoint was not configured. The report uses deterministic scanner output only.",
            "",
            "## Remaining Risks",
            "",
            "- CUDA C++ kernels, custom Triton kernels, and CUDA-only binary dependencies require manual review.",
            "- Uploaded repositories are not executed inside the Space; live validation belongs on AMD Developer Cloud.",
            "- ROCm performance depends on model, batch shape, vLLM version, ROCm version, and GPU instance configuration.",
        ]
    )
    return "\n".join(lines) + "\n"


def generate_cookbook() -> str:
    return """# ROCm Migration Cookbook

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
"""


def generate_feedback() -> str:
    return """# ROCm / AMD Developer Cloud Feedback

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
"""


def write_artifacts(bundle: MigrationBundle, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "rocm_patch.diff": bundle.patch_diff,
        "Dockerfile.rocm": bundle.dockerfile,
        "amd_developer_cloud_runbook.md": bundle.runbook,
        "migration_report.md": bundle.report,
        "benchmark_result.json": json.dumps(bundle.benchmark, indent=2),
        "ROCM_MIGRATION_COOKBOOK.md": bundle.cookbook,
        "ROCM_FEEDBACK.md": bundle.feedback,
    }
    paths: dict[str, str] = {}
    for filename, content in files.items():
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        paths[filename] = str(path)

    bundle_path = output_dir / "rocmport_artifacts.zip"
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, path in paths.items():
            archive.write(path, arcname=filename)
    paths["rocmport_artifacts.zip"] = str(bundle_path)
    return paths
