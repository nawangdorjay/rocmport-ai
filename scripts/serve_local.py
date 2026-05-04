from __future__ import annotations

import traceback
from pathlib import Path

from app import CSS, THEME, demo


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "artifacts" / "server"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "run.log"


def main() -> None:
    LOG_PATH.write_text("starting ROCmPort AI on http://127.0.0.1:7860\n", encoding="utf-8")
    try:
        demo.launch(server_name="127.0.0.1", server_port=7860, theme=THEME, css=CSS, quiet=True)
    except Exception:
        LOG_PATH.write_text(traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
