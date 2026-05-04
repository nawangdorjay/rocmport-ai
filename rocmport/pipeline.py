from __future__ import annotations

from pathlib import Path

from .artifacts import (
    generate_cookbook,
    generate_feedback,
    generate_report,
    generate_rocm_dockerfile,
    generate_runbook,
    load_benchmark,
    write_artifacts,
)
from .models import MigrationBundle
from .ingest import make_work_dir
from .patcher import generate_patch_diff
from .qwen import qwen_summary
from .scanner import scan_repository
from .scoring import calculate_score


def analyze_repository(repo_path: str | Path, output_dir: str | Path | None = None, repo_name: str | None = None) -> MigrationBundle:
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {root}")

    findings = scan_repository(root)
    before_score = calculate_score(findings, after_patch=False)
    after_score = calculate_score(findings, after_patch=True)
    name = repo_name or root.name
    patch_diff = generate_patch_diff(root)
    dockerfile = generate_rocm_dockerfile(name)
    runbook = generate_runbook(name)
    benchmark = load_benchmark()
    cookbook = generate_cookbook()
    feedback = generate_feedback()

    provisional = MigrationBundle(
        repo_name=name,
        findings=findings,
        before_score=before_score,
        after_score=after_score,
        patch_diff=patch_diff,
        dockerfile=dockerfile,
        runbook=runbook,
        report="",
        benchmark=benchmark,
        cookbook=cookbook,
        feedback=feedback,
    )

    qwen_section = qwen_summary(_qwen_prompt(provisional))
    provisional.report = generate_report(provisional, qwen_section)
    artifacts_dir = Path(output_dir) if output_dir else make_work_dir("rocmport-artifacts-")
    provisional.artifact_paths = write_artifacts(provisional, artifacts_dir)
    return provisional


def _qwen_prompt(bundle: MigrationBundle) -> str:
    findings = "\n".join(
        f"- {finding.severity} {finding.category} {finding.path}:{finding.line}: {finding.message}"
        for finding in bundle.findings[:30]
    )
    return f"""Analyze this ROCm migration result for a hackathon demo.

Repository: {bundle.repo_name}
Before score: {bundle.before_score.total}/100
After score: {bundle.after_score.total}/100

Findings:
{findings or "- No findings"}

Write:
1. one concise executive summary,
2. the highest-impact fixes,
3. what to validate on AMD Developer Cloud,
4. one sentence about Qwen/AMD relevance.
"""
