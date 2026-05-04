from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


DEFAULT_QWEN_MODEL = "Qwen/Qwen3-Coder-Next-FP8"


def qwen_summary(prompt: str) -> str | None:
    base_url = os.getenv("QWEN_BASE_URL", "").strip()
    api_key = os.getenv("QWEN_API_KEY", "").strip()
    model = os.getenv("QWEN_MODEL", DEFAULT_QWEN_MODEL).strip() or DEFAULT_QWEN_MODEL
    if not base_url or not api_key:
        return None

    url = _chat_url(base_url)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a concise ROCm migration engineer. Explain migration blockers, fixes, and AMD performance implications.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 900,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        return None


def _chat_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"
