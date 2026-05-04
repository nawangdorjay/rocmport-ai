---
title: ROCmPort AI
sdk: gradio
app_file: app.py
pinned: false
---

# ROCmPort AI

ROCmPort AI is a hackathon-ready Gradio application for scanning CUDA-first AI repositories and generating an AMD ROCm migration package.

It produces:

- AMD Readiness Score before and after deterministic migration fixes
- CUDA/ROCm blocker findings with file and line references
- ROCm-ready patch diff
- `Dockerfile.rocm`
- AMD Developer Cloud runbook
- migration report
- ROCm migration cookbook and feedback notes

The MVP focuses on Python, PyTorch, Hugging Face inference scripts, vLLM/SGLang launch commands, Dockerfiles, and benchmark scripts. It does not attempt CUDA C++ kernel migration.

## Run Locally

```bash
pip install -r requirements.txt
python app.py
```

The app listens on `http://127.0.0.1:7860` by default.

## Optional Qwen Endpoint

ROCmPort AI uses deterministic scanners and patching as the source of truth. If these environment variables are present, it also asks a Qwen-compatible OpenAI API endpoint to improve the migration narrative:

```bash
set QWEN_BASE_URL=https://your-endpoint/v1
set QWEN_API_KEY=your-token
set QWEN_MODEL=Qwen/Qwen3-Coder-Next-FP8
```

If those variables are missing, the app falls back to a deterministic report.

## AMD Benchmark

This workspace cannot run AMD Developer Cloud jobs directly. The included `data/benchmark_result.json` is a transparent pending benchmark record plus the exact collection schema. After running the generated runbook on AMD Developer Cloud, replace it with the measured values and logs.

## Tests

```bash
python -m pytest
```

## Deployment

Create a public Hugging Face Space with the Gradio SDK and upload this repository. Add Qwen endpoint credentials as Space secrets only if you want live Qwen explanations.
