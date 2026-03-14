from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from PIL import Image

from src.checks import find_prohibited_words


def evaluate_compliance(
    output_paths: dict[str, Path],
    expected_sizes: dict[str, tuple[int, int]],
    campaign_message: str,
    prohibited_words: Iterable[str],
    logo_required: bool,
    logo_path: Path | None,
    logo_applied_by_ratio: dict[str, bool],
) -> dict:
    message_present = bool(campaign_message.strip())
    prohibited_hits = find_prohibited_words(campaign_message, prohibited_words)
    logo_configured = logo_path is not None
    logo_file_exists = logo_path.exists() if logo_path is not None else False
    logo_applied = bool(logo_applied_by_ratio) and all(logo_applied_by_ratio.values())

    warnings: list[str] = []
    if not message_present:
        warnings.append("Campaign message is missing.")
    if prohibited_hits:
        warnings.append(
            "Campaign message contains prohibited words: "
            + ", ".join(prohibited_hits)
        )
    if logo_required and not logo_configured:
        warnings.append("Logo is required but no logo path was configured.")
    if logo_required and logo_configured and not logo_file_exists:
        warnings.append("Logo is required but the configured file is missing.")
    if logo_required and logo_file_exists and not logo_applied:
        warnings.append("Logo is required but was not composited onto every output.")

    outputs: dict[str, dict] = {}
    passed = message_present and not prohibited_hits
    if logo_required:
        passed = passed and logo_configured and logo_file_exists and logo_applied

    for ratio_name, expected_size in expected_sizes.items():
        output_path = output_paths.get(ratio_name)
        file_exists = bool(output_path and output_path.exists())
        actual_size = None
        dimensions_match = False
        if file_exists and output_path is not None:
            with Image.open(output_path) as image:
                actual_size = list(image.size)
                dimensions_match = image.size == expected_size
        outputs[ratio_name] = {
            "file_exists": file_exists,
            "expected_size": list(expected_size),
            "actual_size": actual_size,
            "dimensions_match": dimensions_match,
            "logo_applied": logo_applied_by_ratio.get(ratio_name, False),
        }
        passed = passed and file_exists and dimensions_match

    return {
        "passed": passed,
        "warnings": warnings,
        "message_present": message_present,
        "prohibited_words_found": prohibited_hits,
        "logo": {
            "required": logo_required,
            "configured_path": logo_path.as_posix() if logo_path is not None else None,
            "file_exists": logo_file_exists,
            "applied_to_all_outputs": logo_applied,
        },
        "outputs": outputs,
    }
