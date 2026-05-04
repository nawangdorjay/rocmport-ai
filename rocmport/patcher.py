from __future__ import annotations

import difflib
import re
from pathlib import Path

from .ingest import iter_text_files


def generate_patch_diff(root: Path) -> str:
    diff_parts: list[str] = []
    for relative_path, original in iter_text_files(root):
        transformed = transform_text(relative_path, original)
        if transformed == original:
            continue
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            transformed.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        )
        diff_parts.extend(diff)

    if not diff_parts:
        return "# No deterministic patch was generated. Review manual findings in the migration report.\n"
    return "".join(diff_parts)


def transform_text(relative_path: str, text: str) -> str:
    path = Path(relative_path)
    lower_name = path.name.lower()
    suffix = path.suffix.lower()

    if suffix == ".py":
        return _transform_python(text)
    if lower_name.startswith("dockerfile"):
        return _transform_dockerfile(text)
    if suffix in {".sh", ".bash", ".zsh", ".yaml", ".yml", ".txt", ".md"}:
        return _transform_shellish(text)
    return text


def _transform_python(text: str) -> str:
    changed = text
    needs_device = bool(
        re.search(r"\.cuda\s*\(\s*\)", changed)
        or re.search(r"\.to\(\s*['\"]cuda['\"]\s*\)", changed)
        or re.search(r"torch\.device\(\s*['\"]cuda['\"]\s*\)", changed)
    )
    if needs_device and "import torch" in changed and "_rocmport_device" not in changed:
        changed = _insert_device_helper(changed)

    changed = re.sub(r"\.cuda\s*\(\s*\)", ".to(_rocmport_device)", changed)
    changed = re.sub(r"\.to\(\s*['\"]cuda['\"]\s*\)", ".to(_rocmport_device)", changed)
    changed = re.sub(r"torch\.device\(\s*['\"]cuda['\"]\s*\)", "_rocmport_device", changed)
    return changed


def _insert_device_helper(text: str) -> str:
    lines = text.splitlines()
    insert_at = 0
    for index, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_at = index + 1
    helper = [
        "",
        "# ROCm PyTorch exposes AMD GPUs through the torch.cuda namespace.",
        '_rocmport_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")',
    ]
    return "\n".join(lines[:insert_at] + helper + lines[insert_at:]) + ("\n" if text.endswith("\n") else "")


def _transform_dockerfile(text: str) -> str:
    changed = re.sub(
        r"(?im)^\s*FROM\s+nvidia/cuda:[^\n]+",
        "FROM vllm/vllm-openai-rocm:latest",
        text,
    )
    changed = _transform_shellish(changed)
    return changed


def _transform_shellish(text: str) -> str:
    changed = text.replace("nvidia-smi", "rocm-smi")
    changed = changed.replace("NVIDIA_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES")
    changed = changed.replace("CUDA_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES")
    changed = changed.replace("NVIDIA_DRIVER_CAPABILITIES", "ROCM_VISIBLE_DEVICES")
    return changed
