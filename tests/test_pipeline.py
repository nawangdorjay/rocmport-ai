from pathlib import Path

from rocmport.pipeline import analyze_repository


def test_pipeline_generates_artifacts_and_improves_score():
    project_root = Path(__file__).resolve().parents[1]
    root = project_root / "samples" / "cuda_first_repo"
    output_dir = project_root / "artifacts" / "test-output"
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = analyze_repository(root, output_dir=output_dir, repo_name="cuda_first_repo")

    assert bundle.before_score.total < bundle.after_score.total
    assert bundle.after_score.total < 100
    assert "Dockerfile.rocm" in bundle.artifact_paths
    assert "rocmport_artifacts.zip" in bundle.artifact_paths
    assert "vllm/vllm-openai-rocm:latest" in bundle.dockerfile
    assert ".to(_rocmport_device)" in bundle.patch_diff
    assert Path(bundle.artifact_paths["migration_report.md"]).exists()
