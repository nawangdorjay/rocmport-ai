"""
ROCmPort AI — CrewAI Multi-Agent Pipeline
==========================================
Three agents collaborate to migrate a CUDA repository to AMD ROCm:

  Agent 1 — CUDA Migration Auditor
    Tool:   scan_cuda_repository  (wraps rocmport/scanner.py)
    Goal:   Enumerate every blocker with file + line references.

  Agent 2 — ROCm Migration Engineer
    Tool:   generate_rocm_patch  (wraps rocmport/patcher.py)
    Goal:   Apply deterministic fixes, summarise what changed.

  Agent 3 — Migration Report Writer
    Tools:  none (pure reasoning over prior outputs)
    Goal:   Executive summary + AMD/Qwen recommendations.

If CrewAI or the Qwen endpoint is not configured the caller receives
None and pipeline.py falls back to the deterministic path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Optional CrewAI import — soft dependency
# ---------------------------------------------------------------------------
try:
    from crewai import Agent, Crew, Process, Task
    from crewai.tools import tool as crewai_tool

    CREWAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    CREWAI_AVAILABLE = False

from .patcher import generate_patch_diff
from .scanner import scan_repository


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _build_llm() -> Any | None:
    """
    Return a CrewAI LLM object backed by the Qwen OpenAI-compatible endpoint,
    or None if the required environment variables are absent.
    """
    if not CREWAI_AVAILABLE:
        return None

    base_url = os.getenv("QWEN_BASE_URL", "").strip()
    api_key = os.getenv("QWEN_API_KEY", "").strip()
    model = os.getenv("QWEN_MODEL", "Qwen/Qwen3-Coder-Next-FP8").strip() or "Qwen/Qwen3-Coder-Next-FP8"

    if not base_url or not api_key:
        return None

    from crewai import LLM  # noqa: PLC0415

    # LiteLLM expects "openai/<model>" for OpenAI-compatible endpoints.
    return LLM(
        model=f"openai/{model}",
        base_url=base_url,
        api_key=api_key,
        temperature=0.2,
        max_tokens=1200,
    )


# ---------------------------------------------------------------------------
# CrewAI Tools  (wrapping the deterministic rocmport modules)
# ---------------------------------------------------------------------------

def _make_tools(repo_path_str: str):  # type: ignore[return]
    """
    Factory that produces bound CrewAI tools for a given repo path.
    Defining tools inside a function lets us capture the path as a closure
    while still using the @crewai_tool decorator syntax.
    """

    @crewai_tool("scan_cuda_repository")
    def scan_cuda_repository(repo_path: str = repo_path_str) -> str:
        """
        Scan a CUDA-based AI repository and identify all migration blockers.
        Accepts an optional repo_path argument; defaults to the current repo.
        Returns a JSON array of findings with id, category, severity,
        path, line, message, and suggested_fix fields.
        """
        try:
            resolved = str(repo_path).strip() or repo_path_str
            path = Path(resolved)
            findings = scan_repository(path)
            return json.dumps([f.to_dict() for f in findings[:60]], indent=2)
        except Exception as exc:  # pragma: no cover
            return json.dumps({"error": str(exc)})

    @crewai_tool("generate_rocm_patch")
    def generate_rocm_patch(repo_path: str = repo_path_str) -> str:
        """
        Generate a unified diff patch that applies deterministic CUDA-to-ROCm fixes.
        Replaces .cuda() calls, torch.device('cuda') strings, NVIDIA env vars,
        nvidia-smi commands, and NVIDIA Docker base images with ROCm-safe equivalents.
        Accepts an optional repo_path argument; defaults to the current repo.
        Returns the raw unified diff text.
        """
        try:
            resolved = str(repo_path).strip() or repo_path_str
            path = Path(resolved)
            return generate_patch_diff(path)
        except Exception as exc:  # pragma: no cover
            return f"# Error generating patch: {exc}"

    return scan_cuda_repository, generate_rocm_patch


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_agentic_pipeline(root: Path, repo_name: str) -> dict[str, str] | None:
    """
    Execute the CrewAI sequential multi-agent pipeline.

    Returns a dict with keys:
      - "report"        — Markdown report from the Report Writer agent
      - "audit_output"  — Raw output of the Auditor task
      - "patch_output"  — Raw output of the Engineer task

    Returns None if CrewAI is not installed or the Qwen endpoint is absent.
    """
    if not CREWAI_AVAILABLE:
        return None

    llm = _build_llm()
    if llm is None:
        return None

    repo_path_str = str(root)
    scan_tool, patch_tool = _make_tools(repo_path_str)

    # ------------------------------------------------------------------
    # Agent definitions
    # ------------------------------------------------------------------
    auditor = Agent(
        role="CUDA Migration Auditor",
        goal=(
            "Produce a complete, structured list of every CUDA migration blocker "
            "in the repository, grouped by category."
        ),
        backstory=(
            "You are an expert GPU software engineer who has ported dozens of "
            "PyTorch, Hugging Face, and vLLM workloads from NVIDIA CUDA to AMD ROCm. "
            "You know every API, environment variable, Docker image, and pip package "
            "that must change before code can run on AMD Instinct GPUs."
        ),
        tools=[scan_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    engineer = Agent(
        role="ROCm Migration Engineer",
        goal=(
            "Apply deterministic code fixes and generate a ROCm-ready patch diff. "
            "Summarise which files were changed and why."
        ),
        backstory=(
            "You are a senior systems engineer specialising in GPU software migration. "
            "You translate CUDA blocker findings into concrete unified diffs and "
            "ROCm Dockerfiles, ensuring every auto-remediable issue has a matching fix."
        ),
        tools=[patch_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    reporter = Agent(
        role="Migration Report Writer",
        goal=(
            "Synthesise the audit findings and patch summary into a clear Markdown "
            "migration report that a developer can use to validate their workload on "
            "AMD Developer Cloud."
        ),
        backstory=(
            "You are a technical writer and AI infrastructure specialist. "
            "You write concise, actionable reports that bridge the gap between raw "
            "scanner output and the steps a developer needs to take on AMD hardware."
        ),
        tools=[],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # ------------------------------------------------------------------
    # Task definitions
    # ------------------------------------------------------------------
    audit_task = Task(
        description=(
            f"Use the scan_cuda_repository tool to scan the repository at "
            f"'{repo_path_str}'. "
            "List every blocker found, grouped by category "
            "(code, environment, serving, benchmark, deployment). "
            "Include file path, line number, severity (high/medium/low/manual), "
            "and the suggested fix for each finding."
        ),
        expected_output=(
            "A JSON array of all findings. Each element must have: "
            "id, category, severity, path, line, message, suggested_fix."
        ),
        agent=auditor,
    )

    patch_task = Task(
        description=(
            f"Use the generate_rocm_patch tool on '{repo_path_str}' to produce the "
            "deterministic unified diff. Then write a short paragraph (3–5 sentences) "
            "summarising which files were patched and what was changed."
        ),
        expected_output=(
            "The unified diff text followed by a short human-readable summary "
            "of the changes made."
        ),
        agent=engineer,
        context=[audit_task],
    )

    report_task = Task(
        description=(
            f"Write a concise ROCm migration report for the repository '{repo_name}'. "
            "Structure it as Markdown with these sections:\n"
            "1. **Executive Summary** — one paragraph covering what the tool found.\n"
            "2. **Top 3 High-Impact Fixes** — the three most important things a developer "
            "must verify on AMD Developer Cloud before claiming ROCm readiness.\n"
            "3. **AMD & Qwen Recommendation** — explain why running Qwen3-Coder-Next-FP8 "
            "on AMD Instinct MI300X via vLLM is the recommended model backend for this repo.\n"
            "4. **Remaining Risks** — items that need manual review (CUDA C++ kernels, "
            "custom Triton ops, CUDA-only binary wheels)."
        ),
        expected_output=(
            "A Markdown document with four labelled sections: Executive Summary, "
            "Top 3 High-Impact Fixes, AMD & Qwen Recommendation, Remaining Risks."
        ),
        agent=reporter,
        context=[audit_task, patch_task],
    )

    # ------------------------------------------------------------------
    # Crew execution
    # ------------------------------------------------------------------
    crew = Crew(
        agents=[auditor, engineer, reporter],
        tasks=[audit_task, patch_task, report_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    audit_raw = audit_task.output.raw if audit_task.output else ""
    patch_raw = patch_task.output.raw if patch_task.output else ""
    report_raw = str(result)

    return {
        "report": report_raw,
        "audit_output": audit_raw,
        "patch_output": patch_raw,
    }
