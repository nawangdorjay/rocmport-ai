from pathlib import Path

from rocmport.scanner import scan_repository


def test_scanner_finds_cuda_and_nvidia_blockers():
    root = Path(__file__).resolve().parents[1] / "samples" / "cuda_first_repo"
    findings = scan_repository(root)
    messages = "\n".join(f.message for f in findings)

    assert "hardcoded .cuda()" in messages
    assert "NVIDIA CUDA base image" in messages
    assert "NVIDIA-specific GPU inspection command" in messages
    assert any(f.category == "serving" for f in findings)
