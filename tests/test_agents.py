"""Tests for the CrewAI agents module."""

from rocmport.agents import CREWAI_AVAILABLE, _build_llm, _make_tools
from pathlib import Path


def test_agents_module_imports_cleanly():
    """agents.py must import without error regardless of whether crewai is installed."""
    import rocmport.agents  # noqa: F401 — just verifies no import-time crash


def test_crewai_available_is_bool():
    """CREWAI_AVAILABLE must always be a bool (True or False)."""
    assert isinstance(CREWAI_AVAILABLE, bool)


def test_build_llm_returns_none_without_env(monkeypatch):
    """_build_llm() must return None when Qwen env vars are absent."""
    monkeypatch.delenv("QWEN_BASE_URL", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    assert _build_llm() is None


def test_make_tools_returns_two_callables():
    """_make_tools() must return exactly two CrewAI Tool objects with a .run() method."""
    if not CREWAI_AVAILABLE:
        import pytest
        pytest.skip("crewai not installed")
    scan_tool, patch_tool = _make_tools("/tmp/fake_repo")
    # CrewAI Tool objects expose .run(), not __call__
    assert hasattr(scan_tool, "run")
    assert hasattr(patch_tool, "run")


def test_scan_tool_works_on_sample_repo():
    """The scan_cuda_repository tool must return valid JSON on the sample repo."""
    import json
    if not CREWAI_AVAILABLE:
        import pytest
        pytest.skip("crewai not installed")

    sample = Path(__file__).resolve().parents[1] / "samples" / "cuda_first_repo"
    scan_tool, _ = _make_tools(str(sample))
    # CrewAI Tool objects are invoked via .run(), not direct call
    result = scan_tool.run({"repo_path": str(sample)})
    findings = json.loads(result)
    assert isinstance(findings, list)
    assert len(findings) > 0
    assert "severity" in findings[0]
