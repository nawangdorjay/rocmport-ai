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


def analyze_repository(
    repo_path: str | Path,
    output_dir: str | Path | None = None,
    repo_name: str | None = None,
) -> MigrationBundle:
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {root}")

    name = repo_name or root.name

    # --- Deterministic steps (always run) --------------------------------
    findings = scan_repository(root)
    before_score = calculate_score(findings, after_patch=False)
    after_score = calculate_score(findings, after_patch=True)
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

    # --- Agentic path: CrewAI + Qwen (used when env vars are present) ----
    agentic_report = _try_agentic_pipeline(root, name)

    if agentic_report:
        # The CrewAI crew produced the full Markdown report.
        provisional.report = _wrap_agentic_report(agentic_report, provisional)
    else:
        # Fallback: deterministic report + optional Qwen narrative section.
        qwen_section = qwen_summary(_qwen_prompt(provisional))
        provisional.report = generate_report(provisional, qwen_section)

    artifacts_dir = Path(output_dir) if output_dir else make_work_dir("rocmport-artifacts-")
    provisional.artifact_paths = write_artifacts(provisional, artifacts_dir)
    return provisional


# ---------------------------------------------------------------------------
# Agentic pipeline helper
# ---------------------------------------------------------------------------

def _try_agentic_pipeline(root: Path, repo_name: str) -> str | None:
    """
    Attempt to run the CrewAI multi-agent pipeline.
    Returns the Markdown report string produced by the Report Writer agent,
    or None if CrewAI is unavailable or the Qwen endpoint is not configured.
    Errors are swallowed so the deterministic fallback always succeeds.
    """
    try:
        from .agents import CREWAI_AVAILABLE, run_agentic_pipeline  # noqa: PLC0415

        if not CREWAI_AVAILABLE:
            return None

        import os  # noqa: PLC0415
        import io
        from contextlib import redirect_stdout

        if not os.getenv("QWEN_BASE_URL") or not os.getenv("QWEN_API_KEY"):
            return None

        f = io.StringIO()
        with redirect_stdout(f):
            result = run_agentic_pipeline(root, repo_name)
        
        agent_output = result.get("report") if result else None
        if agent_output:
            log_str = f.getvalue().strip()
            # Append the live reasoning logs as an expandable block
            agent_output += "\n\n<details>\n<summary>🧠 View Agent Reasoning Logs</summary>\n\n```text\n"
            agent_output += log_str if log_str else "No verbose logs captured."
            agent_output += "\n```\n</details>\n"
            
        return agent_output
    except Exception:  # pragma: no cover
        return None


def _wrap_agentic_report(agent_report: str, bundle: MigrationBundle) -> str:
    """
    Prepend the standard score table to the agent-generated Markdown report
    so the Report tab in the Gradio UI looks consistent.
    """
    from .artifacts import generate_report  # noqa: PLC0415

    header = generate_report(bundle, qwen_section=None).split("## Qwen Agent Notes")[0]
    return header + "## AI Agent Report (CrewAI + Qwen3-Coder)\n\n" + agent_report + "\n"


# ---------------------------------------------------------------------------
# Qwen prompt helper (used only in deterministic fallback)
# ---------------------------------------------------------------------------

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
