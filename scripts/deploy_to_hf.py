"""
Deploy ROCmPort AI to a Hugging Face Space.

Usage:
    python scripts/deploy_to_hf.py --token hf_xxxx --username nawangdorjay

The script will:
1. Create the Space (Gradio SDK, public) if it doesn't exist
2. Push the repo contents to the Space via huggingface_hub upload_folder
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPACE_NAME = "rocmport-ai"

EXCLUDE_PATTERNS = [
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "pytest-cache-files-*",
    "artifacts/runtime",
    ".git",
    ".tmp",
    ".gradio",
    "*.pyc",
    "*.pyo",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy ROCmPort AI to HF Spaces")
    parser.add_argument("--token", required=True, help="Hugging Face write token (hf_...)")
    parser.add_argument("--username", required=True, help="Hugging Face username or org name")
    parser.add_argument("--space-name", default=SPACE_NAME, help=f"Space name (default: {SPACE_NAME})")
    args = parser.parse_args()

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("ERROR: huggingface_hub is not installed. Run: pip install huggingface_hub")
        sys.exit(1)

    api = HfApi(token=args.token)
    repo_id = f"{args.username}/{args.space_name}"

    # --- 1. Create Space if it doesn't exist ---
    try:
        api.repo_info(repo_id=repo_id, repo_type="space")
        print(f"Space already exists: https://huggingface.co/spaces/{repo_id}")
    except Exception:
        print(f"Creating Space: {repo_id} ...")
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="gradio",
            private=False,
            exist_ok=True,
        )
        print(f"Space created: https://huggingface.co/spaces/{repo_id}")

    # --- 2. Upload all files ---
    print(f"Uploading from {REPO_ROOT} ...")
    api.upload_folder(
        folder_path=str(REPO_ROOT),
        repo_id=repo_id,
        repo_type="space",
        ignore_patterns=EXCLUDE_PATTERNS,
        commit_message="Deploy ROCmPort AI — CUDA-to-ROCm migration scanner",
    )
    print(f"\nDeployed!  https://huggingface.co/spaces/{repo_id}")
    print("   It may take 1-2 minutes for the Space to build and come online.")


if __name__ == "__main__":
    main()
