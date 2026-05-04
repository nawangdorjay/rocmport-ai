from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import gradio as gr

from rocmport.ingest import PreparedRepo, prepare_github_repo, prepare_uploaded_zip, sample_repo_path
from rocmport.models import CATEGORY_LABELS, MigrationBundle
from rocmport.pipeline import analyze_repository


PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = PROJECT_ROOT / "artifacts" / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("ROCMPORT_TMP_DIR", str(RUNTIME_DIR))


def run_analysis(source_mode: str, uploaded_zip: str | None, github_url: str, branch: str) -> tuple[Any, ...]:
    try:
        prepared = _prepare_repo(source_mode, uploaded_zip, github_url, branch)
        output_dir = RUNTIME_DIR / f"rocmport-ui-artifacts-{uuid.uuid4().hex}"
        output_dir.mkdir(parents=True, exist_ok=False)
        bundle = analyze_repository(prepared.path, output_dir=output_dir, repo_name=prepared.name)
        return _format_outputs(bundle)
    except Exception as exc:
        error = f"Analysis failed: {exc}"
        empty_scores = "<div class='score-card'><h2>Analysis failed</h2><p>{}</p></div>".format(error)
        return (
            empty_scores,
            [],
            error,
            "",
            "",
            "",
            error,
            "{}",
            error,
            None,
        )


def _prepare_repo(source_mode: str, uploaded_zip: str | None, github_url: str, branch: str) -> PreparedRepo:
    if source_mode == "Built-in sample":
        sample = sample_repo_path(PROJECT_ROOT)
        return PreparedRepo(path=sample, name="cuda_first_repo")
    if source_mode == "Uploaded ZIP":
        if not uploaded_zip:
            raise ValueError("Upload a ZIP file or switch to the built-in sample.")
        return prepare_uploaded_zip(uploaded_zip)
    if source_mode == "Public GitHub URL":
        if not github_url.strip():
            raise ValueError("Enter a public GitHub repository URL.")
        return prepare_github_repo(github_url, branch.strip() or "main")
    raise ValueError("Unknown source mode.")


def _format_outputs(bundle: MigrationBundle) -> tuple[Any, ...]:
    benchmark_json = json.dumps(bundle.benchmark, indent=2)
    return (
        _score_html(bundle),
        bundle.findings_table(),
        _migration_plan_markdown(bundle),
        bundle.patch_diff,
        bundle.dockerfile,
        bundle.runbook,
        _benchmark_markdown(bundle.benchmark),
        benchmark_json,
        bundle.report,
        bundle.artifact_paths.get("rocmport_artifacts.zip"),
    )


def _score_html(bundle: MigrationBundle) -> str:
    rows = []
    for category, label in CATEGORY_LABELS.items():
        before = bundle.before_score.categories[category]
        after = bundle.after_score.categories[category]
        rows.append(
            f"""
            <tr>
              <td>{label}</td>
              <td><div class="meter"><span style="width:{before}%"></span></div><strong>{before}</strong></td>
              <td><div class="meter after"><span style="width:{after}%"></span></div><strong>{after}</strong></td>
            </tr>
            """
        )
    return f"""
    <div class="score-wrap">
      <div class="score-card">
        <div class="score-label">Before</div>
        <div class="score-number">{bundle.before_score.total}</div>
      </div>
      <div class="score-card">
        <div class="score-label">After deterministic fixes</div>
        <div class="score-number after-text">{bundle.after_score.total}</div>
      </div>
      <div class="score-card">
        <div class="score-label">Findings</div>
        <div class="score-number">{len(bundle.findings)}</div>
      </div>
    </div>
    <table class="score-table">
      <thead><tr><th>Category</th><th>Before</th><th>After</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """


def _migration_plan_markdown(bundle: MigrationBundle) -> str:
    if not bundle.findings:
        return "### Migration Plan\n\nNo blockers were found. Run the generated AMD Developer Cloud smoke test before submission."
    grouped: dict[str, list[str]] = {}
    for finding in bundle.findings:
        grouped.setdefault(finding.category, []).append(
            f"- `{finding.path}:{finding.line}`: {finding.suggested_fix}"
        )
    sections = ["### Migration Plan"]
    for category, label in CATEGORY_LABELS.items():
        if category not in grouped:
            continue
        sections.append(f"\n#### {label}\n" + "\n".join(grouped[category][:8]))
    return "\n".join(sections)


def _benchmark_markdown(benchmark: dict[str, Any]) -> str:
    verified = benchmark.get("verified", False)
    status = "Verified AMD Developer Cloud run" if verified else "Pending AMD Developer Cloud run"
    lines = [
        f"### {status}",
        "",
        f"- Hardware: `{benchmark.get('hardware', 'not captured')}`",
        f"- ROCm: `{benchmark.get('rocm_version', 'not captured')}`",
        f"- vLLM: `{benchmark.get('vllm_version', 'not captured')}`",
        f"- Model: `{benchmark.get('model', 'not captured')}`",
        f"- Throughput tokens/sec: `{benchmark.get('throughput_tokens_per_second', 'not captured')}`",
        f"- P50 latency ms: `{benchmark.get('p50_latency_ms', 'not captured')}`",
        f"- Peak VRAM GB: `{benchmark.get('peak_vram_gb', 'not captured')}`",
        "",
        benchmark.get("notes", "Run the generated AMD Developer Cloud runbook to replace this record with measured values."),
    ]
    return "\n".join(lines)


CSS = """
.gradio-container { max-width: 1280px !important; }
.score-wrap {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 8px 0 16px;
}
.score-card {
  border: 1px solid #d9dee7;
  border-radius: 8px;
  padding: 14px;
  background: #ffffff;
}
.score-label {
  color: #5d6675;
  font-size: 13px;
  margin-bottom: 8px;
}
.score-number {
  color: #171b22;
  font-size: 34px;
  line-height: 1;
  font-weight: 700;
}
.after-text { color: #087f5b; }
.score-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
}
.score-table th,
.score-table td {
  border-bottom: 1px solid #e6e9ef;
  padding: 8px;
  text-align: left;
}
.meter {
  width: calc(100% - 48px);
  height: 8px;
  background: #edf0f5;
  border-radius: 4px;
  display: inline-block;
  vertical-align: middle;
  margin-right: 8px;
}
.meter span {
  display: block;
  height: 100%;
  background: #525866;
  border-radius: 4px;
}
.meter.after span { background: #087f5b; }
"""


THEME = gr.themes.Base()


with gr.Blocks(title="ROCmPort AI") as demo:
    gr.Markdown("# ROCmPort AI")
    gr.Markdown("CUDA-to-ROCm migration scanner for PyTorch, Hugging Face, and vLLM repositories.")

    with gr.Row():
        source_mode = gr.Radio(
            choices=["Built-in sample", "Uploaded ZIP", "Public GitHub URL"],
            value="Built-in sample",
            label="Repository source",
        )
        uploaded_zip = gr.File(label="Repository ZIP", type="filepath", file_types=[".zip"])
    with gr.Row():
        github_url = gr.Textbox(label="GitHub URL", placeholder="https://github.com/owner/repo")
        branch = gr.Textbox(label="Branch", value="main")

    analyze_button = gr.Button("Analyze repository", variant="primary")

    with gr.Tabs():
        with gr.Tab("Scan"):
            score_html = gr.HTML(label="AMD Readiness Score")
            findings_table = gr.Dataframe(
                headers=["Severity", "Category", "Path", "Line", "Finding", "Suggested fix"],
                label="Findings",
                wrap=True,
            )
            migration_plan = gr.Markdown(label="Migration Plan")
        with gr.Tab("Patch"):
            patch_diff = gr.Code(label="rocm_patch.diff", language=None, lines=20)
            dockerfile = gr.Code(label="Dockerfile.rocm", language="dockerfile", lines=18)
            runbook = gr.Markdown(label="AMD Developer Cloud Runbook")
        with gr.Tab("Benchmark"):
            benchmark_md = gr.Markdown(label="Benchmark Summary")
            benchmark_json = gr.Code(label="benchmark_result.json", language="json", lines=18)
        with gr.Tab("Report"):
            report_md = gr.Markdown(label="Migration Report")
            artifact_zip = gr.File(label="Download migration artifact bundle")

    analyze_button.click(
        fn=run_analysis,
        inputs=[source_mode, uploaded_zip, github_url, branch],
        outputs=[
            score_html,
            findings_table,
            migration_plan,
            patch_diff,
            dockerfile,
            runbook,
            benchmark_md,
            benchmark_json,
            report_md,
            artifact_zip,
        ],
    )


if __name__ == "__main__":
    server_name = os.getenv("GRADIO_SERVER_NAME") or ("0.0.0.0" if os.getenv("SPACE_ID") else "127.0.0.1")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    demo.launch(server_name=server_name, server_port=server_port, theme=THEME, css=CSS, quiet=True)
