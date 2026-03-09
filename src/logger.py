from __future__ import annotations

import json
from pathlib import Path


def write_run_log(campaign_output_dir: Path, run_log: dict) -> Path:
    campaign_output_dir.mkdir(parents=True, exist_ok=True)
    log_path = campaign_output_dir / "run_log.json"
    with log_path.open("w", encoding="utf-8") as handle:
        json.dump(run_log, handle, indent=2)
    return log_path
